import re
import unicodedata
import uuid
from datetime import datetime
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.identifier import Identifier
from app.models.identity_anchor import ConfirmedProfileReference, IdentityAlias, IdentityAnchor
from app.schemas.identity_anchor import (
    ConfirmedProfileResponse,
    CreateConfirmedProfileRequest,
    CreateIdentityAliasRequest,
    IdentityAliasResponse,
    IdentityAnchorSummaryResponse,
    VerifiedIdentifierSummary,
)


class IdentityAnchorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_anchor(self, user_id: uuid.UUID) -> IdentityAnchor:
        result = await self.session.execute(select(IdentityAnchor).where(IdentityAnchor.user_id == user_id))
        anchor = result.scalar_one_or_none()
        if not anchor:
            anchor = IdentityAnchor(user_id=user_id)
            self.session.add(anchor)
            await self.session.flush()
            # Log creation
            audit_event = AuditLog(
                user_id=user_id,
                action="identity_anchor_created",
                resource_type="identity_anchor",
                resource_id=str(anchor.id),
                status="success",
            )
            self.session.add(audit_event)
            await self.session.flush()
        return anchor

    async def _increment_version(self, anchor: IdentityAnchor) -> None:
        anchor.version += 1
        self.session.add(anchor)

    def _canonicalize_alias(self, alias_type: str, value: str) -> str:
        # Strip whitespace
        val = value.strip()
        # Reject control characters
        if any(unicodedata.category(c)[0] == "C" for c in val):
            raise HTTPException(status_code=400, detail="Alias contains invalid control characters")
        if len(val) > 255 or len(val) == 0:
            raise HTTPException(status_code=400, detail="Alias length invalid")
        
        # Unicode normalization
        val = unicodedata.normalize("NFKC", val)
        
        # Type-aware rules
        if alias_type in ("username", "handle"):
            # Lowercase for usernames where it's semantically safe on most platforms
            val = val.lower()
            if val.startswith("@"):
                val = val[1:]
        elif alias_type == "email":
            val = val.lower()
            
        return val

    def _canonicalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise HTTPException(status_code=400, detail="Profile URL scheme must be http or https")
        if parsed.username or parsed.password:
            raise HTTPException(status_code=400, detail="Profile URL cannot contain embedded credentials")
        if not parsed.hostname:
            raise HTTPException(status_code=400, detail="Profile URL must contain a valid hostname")
        
        host = parsed.hostname.lower()
        if host.startswith("www."):
            host = host[4:]
            
        path = parsed.path.rstrip("/")
        # canonical is scheme + normalized host + path (ignoring query params/fragments for identity)
        # unless query params are necessary (e.g. ?id=123), but for profiles we assume paths.
        # This is a safe baseline.
        canonical = f"{parsed.scheme}://{host}{path}"
        if len(canonical) > 1000:
            raise HTTPException(status_code=400, detail="Profile URL is too long")
        return canonical

    async def add_alias(self, user_id: uuid.UUID, request: CreateIdentityAliasRequest) -> IdentityAliasResponse:
        anchor = await self.get_or_create_anchor(user_id)
        
        canonical_val = self._canonicalize_alias(request.alias_type, request.value)
        
        # Check for active duplicates
        result = await self.session.execute(
            select(IdentityAlias)
            .where(
                IdentityAlias.anchor_id == anchor.id,
                IdentityAlias.alias_type == request.alias_type,
                IdentityAlias.value_canonical == canonical_val,
                IdentityAlias.status == "active"
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Idempotent or conflict. Instructions: return a stable canonical conflict according to existing API conventions.
            # Using 409 Conflict.
            raise HTTPException(status_code=409, detail="This alias is already active on your identity anchor.")
            
        alias = IdentityAlias(
            user_id=user_id,
            anchor_id=anchor.id,
            alias_type=request.alias_type,
            value_display=request.value.strip(),
            value_canonical=canonical_val,
            status="active",
            confirmation_method="user_asserted",
            last_confirmed_at=datetime.utcnow()
        )
        self.session.add(alias)
        await self._increment_version(anchor)
        
        audit_event = AuditLog(
            user_id=user_id,
            action="identity_alias_added",
            resource_type="identity_alias",
            resource_id=str(alias.id),
            status="success",
            metadata={"alias_type": alias.alias_type, "confirmation_method": "user_asserted"}
        )
        self.session.add(audit_event)
        
        await self.session.commit()
        await self.session.refresh(alias)
        return IdentityAliasResponse.model_validate(alias)

    async def revoke_alias(self, user_id: uuid.UUID, alias_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(IdentityAlias).where(IdentityAlias.id == alias_id, IdentityAlias.user_id == user_id)
        )
        alias = result.scalar_one_or_none()
        if not alias:
            raise HTTPException(status_code=404, detail="Alias not found")
        
        if alias.status == "revoked":
            return # Idempotent
            
        alias.status = "revoked"
        alias.revoked_at = datetime.utcnow()
        
        anchor = await self.get_or_create_anchor(user_id)
        await self._increment_version(anchor)
        
        audit_event = AuditLog(
            user_id=user_id,
            action="identity_alias_revoked",
            resource_type="identity_alias",
            resource_id=str(alias.id),
            status="success",
        )
        self.session.add(audit_event)
        await self.session.commit()

    async def add_confirmed_profile(self, user_id: uuid.UUID, request: CreateConfirmedProfileRequest) -> ConfirmedProfileResponse:
        anchor = await self.get_or_create_anchor(user_id)
        
        url_str = str(request.profile_url)
        canonical_val = self._canonicalize_url(url_str)
        
        result = await self.session.execute(
            select(ConfirmedProfileReference)
            .where(
                ConfirmedProfileReference.anchor_id == anchor.id,
                ConfirmedProfileReference.profile_url_canonical == canonical_val,
                ConfirmedProfileReference.status == "active"
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="This profile is already active on your identity anchor.")
            
        profile = ConfirmedProfileReference(
            user_id=user_id,
            anchor_id=anchor.id,
            platform=request.platform.lower(),
            profile_url_display=url_str,
            profile_url_canonical=canonical_val,
            username_hint=request.username_hint,
            status="active",
            confirmation_method="user_asserted",
            last_confirmed_at=datetime.utcnow()
        )
        self.session.add(profile)
        await self._increment_version(anchor)
        
        audit_event = AuditLog(
            user_id=user_id,
            action="confirmed_profile_added",
            resource_type="confirmed_profile_reference",
            resource_id=str(profile.id),
            status="success",
            metadata={"platform": profile.platform, "confirmation_method": "user_asserted"}
        )
        self.session.add(audit_event)
        
        await self.session.commit()
        await self.session.refresh(profile)
        return ConfirmedProfileResponse.model_validate(profile)

    async def revoke_profile(self, user_id: uuid.UUID, profile_id: uuid.UUID) -> None:
        result = await self.session.execute(
            select(ConfirmedProfileReference).where(ConfirmedProfileReference.id == profile_id, ConfirmedProfileReference.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile reference not found")
            
        if profile.status == "revoked":
            return
            
        profile.status = "revoked"
        profile.revoked_at = datetime.utcnow()
        
        anchor = await self.get_or_create_anchor(user_id)
        await self._increment_version(anchor)
        
        audit_event = AuditLog(
            user_id=user_id,
            action="confirmed_profile_revoked",
            resource_type="confirmed_profile_reference",
            resource_id=str(profile.id),
            status="success",
        )
        self.session.add(audit_event)
        await self.session.commit()

    async def get_anchor_summary(self, user_id: uuid.UUID) -> IdentityAnchorSummaryResponse:
        anchor = await self.get_or_create_anchor(user_id)
        
        # 1. Fetch active verified identifiers
        id_result = await self.session.execute(
            select(Identifier).where(
                Identifier.user_id == user_id,
                Identifier.is_verified == True
            )
        )
        identifiers = id_result.scalars().all()
        
        # 2. Fetch active aliases
        al_result = await self.session.execute(
            select(IdentityAlias).where(
                IdentityAlias.anchor_id == anchor.id,
                IdentityAlias.status == "active"
            )
        )
        aliases = al_result.scalars().all()
        
        # 3. Fetch active profiles
        prof_result = await self.session.execute(
            select(ConfirmedProfileReference).where(
                ConfirmedProfileReference.anchor_id == anchor.id,
                ConfirmedProfileReference.status == "active"
            )
        )
        profiles = prof_result.scalars().all()
        
        return IdentityAnchorSummaryResponse(
            id=anchor.id,
            version=anchor.version,
            verified_identifiers=[VerifiedIdentifierSummary(
                id=i.id, type=i.type, value_display=i.value_display, verified_at=i.verified_at
            ) for i in identifiers],
            active_aliases=[IdentityAliasResponse.model_validate(a) for a in aliases],
            active_confirmed_profiles=[ConfirmedProfileResponse.model_validate(p) for p in profiles],
            updated_at=anchor.updated_at
        )
