from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.registry import build_connectors
from app.connectors.sdk.rate_limiter import RateLimiter, RateLimitExceeded
from app.connectors.sdk.redis_clients import get_cache_redis
from app.connectors.sdk.types import ConnectorContext, ConnectorResult
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.connector_config import ConnectorConfig
from app.services.audit_service import AuditService
from app.services.consent_service import ConsentService
from app.services.identifier_service import IdentifierService

logger = get_logger(__name__)


class ConnectorService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.identifiers = IdentifierService(session)
        self.consent = ConsentService(session)
        self.audit = AuditService(session)
        self.settings = get_settings()

    async def list_catalog(self) -> list[dict[str, Any]]:
        connectors = await build_connectors()
        db_flags = await self._load_db_flags()
        out = []
        for cid, c in connectors.items():
            cap = c.capability
            env_on = c.is_enabled_by_config()
            db_on = db_flags.get(cid)
            effective = env_on if db_on is None else (env_on and db_on)
            out.append(
                {
                    "id": cap.id,
                    "name": cap.name,
                    "layer": cap.layer.value,
                    "legality": cap.legality.value,
                    "requires_paid_key": cap.requires_paid_key,
                    "sends_identifier": cap.sends_identifier,
                    "supported_identifier_types": cap.supported_identifier_types,
                    "attribution": cap.attribution,
                    "description": cap.description,
                    "enabled_env": env_on,
                    "enabled_db": db_on,
                    "enabled_effective": effective,
                }
            )
        return out

    async def set_enabled(self, connector_id: str, enabled: bool, notes: str | None = None) -> dict:
        connectors = await build_connectors()
        if connector_id not in connectors:
            raise HTTPException(status_code=404, detail="Unknown connector")
        result = await self.session.execute(
            select(ConnectorConfig).where(ConnectorConfig.connector_id == connector_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            row = ConnectorConfig(connector_id=connector_id, enabled=enabled, notes=notes)
            self.session.add(row)
        else:
            row.enabled = enabled
            if notes is not None:
                row.notes = notes
        await self.session.flush()
        await self.audit.log(
            "connector.config_updated",
            details={"connector_id": connector_id, "enabled": enabled},
        )
        return {"connector_id": connector_id, "enabled": enabled}

    async def _load_db_flags(self) -> dict[str, bool]:
        result = await self.session.execute(select(ConnectorConfig))
        return {r.connector_id: r.enabled for r in result.scalars().all()}

    async def probe(
        self,
        user_id: uuid.UUID,
        identifier_id: uuid.UUID,
        connector_ids: list[str] | None = None,
        *,
        password_plaintext: str | None = None,
    ) -> dict[str, Any]:
        """
        Dry-run free surface connectors for a VERIFIED identifier.
        Does NOT persist findings (Sprint 4). Returns observations for UI/debug.
        """
        # G1 gate
        ident = await self.identifiers.require_verified(user_id, identifier_id)

        # Per-user daily probe quota
        redis = await get_cache_redis()
        rl = RateLimiter(redis)
        try:
            await rl.acquire_user_quota(str(user_id))
        except RateLimitExceeded:
            raise HTTPException(status_code=429, detail="Daily probe quota exceeded")

        connectors = await build_connectors()
        db_flags = await self._load_db_flags()

        if connector_ids:
            selected = {k: connectors[k] for k in connector_ids if k in connectors}
        else:
            # Default set by identifier type
            selected = {
                k: c
                for k, c in connectors.items()
                if c.supports(ident.type) and k != "pwned_passwords"
            }

        # Special: password probe
        if password_plaintext is not None and "pwned_passwords" in (connector_ids or ["pwned_passwords"]):
            selected["pwned_passwords"] = connectors["pwned_passwords"]

        results: list[dict[str, Any]] = []
        for cid, connector in selected.items():
            env_on = connector.is_enabled_by_config()
            db_on = db_flags.get(cid)
            effective = env_on if db_on is None else (env_on and db_on)

            purpose = f"discovery.{cid}"
            if connector.capability.sends_identifier:
                ok = await self.consent.ensure_consent(
                    user_id, purpose=purpose, auto_grant=False, scope=ident.type
                )
                if not ok:
                    # Auto-grant only if user explicitly probes? Prefer explicit consent endpoint first.
                    # For better UX in MVP self-scan: auto_grant=True on probe with audit
                    await self.consent.ensure_consent(
                        user_id, purpose=purpose, auto_grant=True, scope=str(ident.id)
                    )

            if cid == "pwned_passwords":
                if not password_plaintext:
                    results.append(
                        ConnectorResult(
                            connector_id=cid,
                            success=False,
                            skipped=True,
                            skip_reason="password_required",
                        ).to_dict()
                    )
                    continue
                ctx = ConnectorContext(
                    user_id=user_id,
                    identifier_id=ident.id,
                    identifier_type="password",
                    identifier_canonical=password_plaintext,
                    consent_purpose=purpose,
                )
            else:
                ctx = ConnectorContext(
                    user_id=user_id,
                    identifier_id=ident.id,
                    identifier_type=ident.type,
                    identifier_canonical=ident.value_canonical,
                    consent_purpose=purpose,
                )

            result = await connector.run(ctx, enabled_override=effective)

            # Egress ledger for identifier-sending connectors (best-effort host)
            if connector.capability.sends_identifier and not result.skipped:
                host = {
                    "xposedornot": "api.xposedornot.com",
                    "crtsh": "crt.sh",
                    "rdap": "rdap.org",
                    "github": "api.github.com",
                    "username_presence": "multi",
                    "serp_ddg": "html.duckduckgo.com",
                }.get(cid, cid)
                await self.consent.record_egress(
                    purpose=purpose,
                    destination_host=host,
                    method="GET",
                    status_code=200 if result.success else None,
                    success=result.success,
                    user_id=user_id,
                    identifier_id=ident.id,
                    summary={
                        "connector": cid,
                        "cache_hit": result.cache_hit,
                        "skipped": result.skipped,
                        "observation_count": len(result.observations),
                    },
                )

            results.append(result.to_dict())

        await self.audit.log(
            "connector.probe",
            user_id=user_id,
            resource_type="identifier",
            resource_id=str(ident.id),
            details={
                "connectors": list(selected.keys()),
                "result_count": len(results),
            },
        )

        # Aggregate attribution for UI
        attributions = sorted(
            {
                r.get("meta", {}).get("attribution")
                or next(
                    (
                        o.get("attribution")
                        for o in r.get("observations") or []
                        if o.get("attribution")
                    ),
                    None,
                )
                for r in results
            }
            - {None}
        )

        return {
            "identifier_id": str(ident.id),
            "identifier_type": ident.type,
            "results": results,
            "attributions": attributions,
            "note": "Probe only — findings persistence & PDSS land in Sprint 4–5. XposedOrNot is primary free breach source.",
        }
