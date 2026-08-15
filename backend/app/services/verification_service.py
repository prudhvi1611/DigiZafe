from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.canonicalize import IdentifierType
from app.repositories.identifier_repository import IdentifierRepository
from app.schemas.identifier import VerificationStartResponse
from app.security.egress import EgressBlockedError, EgressError, get_egress_fetcher
from app.services.audit_service import AuditService
from app.services.consent_service import ConsentService

logger = get_logger(__name__)


class VerificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = IdentifierRepository(session)
        self.audit = AuditService(session)
        self.consent = ConsentService(session)
        self.egress = get_egress_fetcher()
        self.settings = get_settings()

    async def start(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        method: str | None = None,
    ) -> VerificationStartResponse:
        ident = await self.repo.get(identifier_id, user_id)
        if not ident:
            raise HTTPException(status_code=404, detail="Identifier not found")
        if ident.is_verified:
            raise HTTPException(status_code=400, detail="Already verified")

        itype = IdentifierType(ident.type)
        method = (method or self._default_method(itype)).lower()

        if method == "email_code":
            if itype not in (IdentifierType.EMAIL, IdentifierType.PHONE, IdentifierType.USERNAME):
                raise HTTPException(status_code=400, detail="email_code only for email, phone, or username identifiers")
            return await self._start_email_code(user_id, ident, itype)
        if method == "dns_txt":
            if itype != IdentifierType.DOMAIN:
                raise HTTPException(status_code=400, detail="dns_txt only for domain identifiers")
            return await self._start_dns_txt(user_id, ident)
        if method == "github_proof":
            if itype != IdentifierType.GITHUB_USERNAME:
                raise HTTPException(status_code=400, detail="github_proof only for github_username")
            return await self._start_github_proof(user_id, ident)

        raise HTTPException(status_code=400, detail=f"Unsupported method: {method}")

    def _default_method(self, itype: IdentifierType) -> str:
        return {
            IdentifierType.EMAIL: "email_code",
            IdentifierType.DOMAIN: "dns_txt",
            IdentifierType.GITHUB_USERNAME: "github_proof",
            IdentifierType.USERNAME: "email_code",
            IdentifierType.PHONE: "email_code",
        }.get(itype, "email_code")

    async def _start_email_code(self, user_id: uuid.UUID, ident, itype: IdentifierType) -> VerificationStartResponse:
        code = self.repo.new_numeric_code(self.settings.verification_email_code_length)
        ch = await self.repo.create_challenge(
            identifier_id=ident.id,
            user_id=user_id,
            method="email_code",
            raw_secret=code,
            public_payload={"channel": itype.value, "hint": "Enter the code (dev: returned in response)"},
            ttl_minutes=self.settings.verification_token_ttl_minutes,
        )
        # MVP free path: no SMTP required — log + optional expose
        logger.info(
            "verification_email_code_issued",
            user_id=str(user_id),
            identifier_id=str(ident.id),
            # never log full email in prod pipelines if avoidable
        )
        await self.audit.log(
            "verification.started",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": "email_code", "channel": itype.value},
        )
        dev_code = code if self.settings.verification_dev_expose_code and self.settings.is_development else None
        
        channel_name = {
            IdentifierType.PHONE: "phone",
            IdentifierType.USERNAME: "username account",
        }.get(itype, "email")
        
        return VerificationStartResponse(
            challenge_id=ch.id,
            method="email_code",
            expires_at=ch.expires_at,
            instructions={
                "message": f"Enter the verification code sent to your {channel_name}.",
                "dev_note": "In development the code is returned in dev_code when VERIFICATION_DEV_EXPOSE_CODE=true",
            },
            dev_code=dev_code,
        )

    async def _start_dns_txt(self, user_id: uuid.UUID, ident) -> VerificationStartResponse:
        token = self.repo.new_token()
        record_name = f"_digizafe-verify.{ident.value_canonical}"
        record_value = f"digizafe-verification={token}"
        ch = await self.repo.create_challenge(
            identifier_id=ident.id,
            user_id=user_id,
            method="dns_txt",
            raw_secret=token,
            public_payload={
                "record_type": "TXT",
                "record_name": record_name,
                "record_value": record_value,
            },
            ttl_minutes=self.settings.verification_token_ttl_minutes,
        )
        await self.audit.log(
            "verification.started",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": "dns_txt"},
        )
        return VerificationStartResponse(
            challenge_id=ch.id,
            method="dns_txt",
            expires_at=ch.expires_at,
            instructions={
                "message": "Create the following DNS TXT record, wait for propagation, then confirm.",
                "record_type": "TXT",
                "record_name": record_name,
                "record_value": record_value,
                "also_accepted_on_apex": f"TXT on {ident.value_canonical} containing digizafe-verification={token}",
            },
        )

    async def _start_github_proof(self, user_id: uuid.UUID, ident) -> VerificationStartResponse:
        token = self.repo.new_token()
        # User creates a public gist OR puts token in a public repo README — we check via API
        # Simple free proof: create a public gist named digizafe-verify.txt containing the token
        ch = await self.repo.create_challenge(
            identifier_id=ident.id,
            user_id=user_id,
            method="github_proof",
            raw_secret=token,
            public_payload={
                "username": ident.value_canonical,
                "token": token,  # public by design — ownership proof
                "instruction": (
                    f"Create a public gist owned by {ident.value_canonical} "
                    f"with filename digizafe-verify.txt containing exactly: {token}"
                ),
            },
            ttl_minutes=self.settings.verification_token_ttl_minutes,
        )
        await self.audit.log(
            "verification.started",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": "github_proof"},
        )
        return VerificationStartResponse(
            challenge_id=ch.id,
            method="github_proof",
            expires_at=ch.expires_at,
            instructions=ch.public_payload or {},
        )

    async def confirm(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        challenge_id: uuid.UUID,
        code: str | None = None,
    ) -> dict[str, Any]:
        ident = await self.repo.get(identifier_id, user_id)
        if not ident:
            raise HTTPException(status_code=404, detail="Identifier not found")
        ch = await self.repo.get_challenge(challenge_id, user_id)
        if not ch or ch.identifier_id != ident.id:
            raise HTTPException(status_code=404, detail="Challenge not found")
        if ch.consumed_at is not None:
            raise HTTPException(status_code=400, detail="Challenge already used")
        if ch.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=400, detail="Challenge expired")

        ch.attempts += 1
        await self.session.flush()
        if ch.attempts > 10:
            raise HTTPException(status_code=429, detail="Too many attempts")

        ok = False
        if ch.method == "email_code":
            if not code:
                raise HTTPException(status_code=400, detail="code required")
            ok = self.repo.verify_secret(code.strip(), ch.secret_hash)
        elif ch.method == "dns_txt":
            ok = await self._check_dns_txt(ident, ch)
        elif ch.method == "github_proof":
            ok = await self._check_github_proof(user_id, ident, ch)
        else:
            raise HTTPException(status_code=400, detail="Unknown method")

        if not ok:
            await self.audit.log(
                "verification.failed",
                user_id=user_id,
                resource_type="identifier",
                resource_id=str(ident.id),
                details={"method": ch.method},
            )
            raise HTTPException(status_code=400, detail="Verification failed")

        await self.repo.consume_challenge(ch)
        await self.repo.mark_verified(ident, method=ch.method)
        await self.audit.log(
            "verification.succeeded",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": ch.method},
        )
        return {"message": "Identifier verified", "identifier_id": str(ident.id), "method": ch.method}

    async def _check_dns_txt(self, ident, ch) -> bool:
        """Resolve TXT via public DNS (dnspython) — no EgressFetcher HTTP needed."""
        import dns.asyncresolver
        import dns.rdatatype

        token = None
        # Recover token from public payload (it's ownership proof material)
        payload = ch.public_payload or {}
        record_value = payload.get("record_value", "")
        if "digizafe-verification=" in record_value:
            token = record_value.split("digizafe-verification=", 1)[-1].strip()
        if not token:
            return False

        names = [
            payload.get("record_name") or f"_digizafe-verify.{ident.value_canonical}",
            ident.value_canonical,
        ]
        resolver = dns.asyncresolver.Resolver()
        resolver.nameservers = ["1.1.1.1", "8.8.8.8"]  # public free resolvers
        resolver.lifetime = 10.0

        for name in names:
            try:
                answers = await resolver.resolve(name, "TXT")
            except Exception as e:
                logger.info("dns_txt_lookup_failed", name=name, error=str(e))
                continue
            for rdata in answers:
                # rdata.strings is list of bytes
                texts = []
                if hasattr(rdata, "strings"):
                    texts = [s.decode("utf-8", errors="replace") if isinstance(s, bytes) else str(s) for s in rdata.strings]
                else:
                    texts = [str(rdata).strip('"')]
                for t in texts:
                    if f"digizafe-verification={token}" in t or t.strip() == token:
                        # Also verify hash matches challenge
                        if self.repo.verify_secret(token, ch.secret_hash):
                            return True
        return False

    async def _check_github_proof(self, user_id: uuid.UUID, ident, ch) -> bool:
        """List public gists for user via GitHub API (free, rate-limited) through EgressFetcher."""
        payload = ch.public_payload or {}
        token = payload.get("token")
        username = ident.value_canonical
        if not token or not self.repo.verify_secret(token, ch.secret_hash):
            return False

        # Consent for sending username to GitHub
        await self.consent.ensure_consent(
            user_id,
            purpose="verification.github",
            auto_grant=True,  # explicit user action of starting verification
            scope=username,
        )

        url = f"https://api.github.com/users/{username}/gists?per_page=30"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"

        try:
            resp = await self.egress.fetch(
                url,
                headers=headers,
                purpose="verification.github",
            )
            await self.consent.record_egress(
                purpose="verification.github",
                destination_host="api.github.com",
                method="GET",
                status_code=resp.status_code,
                success=resp.status_code == 200,
                user_id=user_id,
                identifier_id=ident.id,
                summary={"username": username},
            )
        except (EgressError, EgressBlockedError) as e:
            logger.warning("github_egress_failed", error=str(e))
            return False

        if resp.status_code != 200:
            return False

        try:
            gists = json.loads(resp.body.decode("utf-8"))
        except Exception:
            return False

        if not isinstance(gists, list):
            return False

        for gist in gists:
            files = gist.get("files") or {}
            for fname, meta in files.items():
                if fname != "digizafe-verify.txt":
                    continue
                # Prefer raw_url fetch via egress
                raw_url = meta.get("raw_url")
                if not raw_url:
                    continue
                try:
                    raw_resp = await self.egress.fetch(
                        raw_url,
                        purpose="verification.github.raw",
                    )
                    await self.consent.record_egress(
                        purpose="verification.github.raw",
                        destination_host=urlparse(raw_url).hostname or "githubusercontent.com",
                        method="GET",
                        status_code=raw_resp.status_code,
                        success=raw_resp.status_code == 200,
                        user_id=user_id,
                        identifier_id=ident.id,
                    )
                    body = raw_resp.body.decode("utf-8", errors="replace").strip()
                    if token in body:
                        # Optional: ensure gist owner matches
                        owner = (gist.get("owner") or {}).get("login", "").lower()
                        if owner and owner != username.lower():
                            continue
                        return True
                except Exception as e:
                    logger.info("gist_raw_fetch_failed", error=str(e))
                    continue
        return False

    async def revalidate(self, user_id: uuid.UUID, identifier_id: uuid.UUID) -> dict[str, Any]:
        """
        Re-check ownership for already-verified identifiers.
        Email: requires new challenge (user in loop).
        Domain: re-query TXT if we stored method dns_txt — for MVP mark revalidated only if still verified flag.
        Full re-proof can re-run start/confirm.
        """
        ident = await self.repo.get(identifier_id, user_id)
        if not ident:
            raise HTTPException(status_code=404, detail="Identifier not found")
        if not ident.is_verified:
            raise HTTPException(status_code=400, detail="Not verified yet")

        # Policy: domain revalidation can re-check last DNS method if we keep token — we don't.
        # Sprint 2: touch last_revalidated_at and audit; deep re-proof via new challenge.
        await self.repo.mark_revalidated(ident)
        await self.audit.log(
            "verification.revalidated",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={"method": ident.verification_method, "mode": "touch"},
        )
        return {
            "message": "Revalidation timestamp updated",
            "last_revalidated_at": ident.last_revalidated_at.isoformat() if ident.last_revalidated_at else None,
            "note": "For cryptographic re-proof, start a new verification challenge.",
        }
