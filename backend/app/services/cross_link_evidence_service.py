import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.models.identity_cross_link import IdentityCrossLinkObservation

logger = logging.getLogger(__name__)

class CrossLinkEvidenceService:
    """
    Manages bounded extraction, canonicalization, and deduplication of cross-links
    originating from Candidates or ConfirmedProfiles.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    def canonicalize_url(self, url: str) -> str | None:
        """
        Normalize URL for canonicalization and deduplication.
        E.g. lowercases host, removes trailing slash and fragments/utm parameters.
        """
        if not url:
            return None
            
        try:
            parsed = urlparse(url.strip())
            if not parsed.scheme or not parsed.hostname:
                return None
            
            scheme = parsed.scheme.lower()
            if scheme not in {"http", "https"}:
                return None
                
            host = parsed.hostname.lower()
            if host.startswith("www."):
                host = host[4:]
                
            path = parsed.path.rstrip("/")
            
            # Simple parameter stripping (MVP just keeps basic paths)
            canonical = f"{scheme}://{host}{path}"
            return canonical
        except Exception:
            return None

    async def record_observation(
        self,
        user_id: uuid.UUID,
        source_entity_id: uuid.UUID,
        source_entity_type: str,
        target_url: str,
        observation_source: str,
        provenance: dict | None = None
    ) -> IdentityCrossLinkObservation | None:
        """
        Record a cross-link observation. Deduplicates against existing canonical URL
        from the same source entity.
        """
        if not self.settings.feature_identity_cross_links:
            return None
            
        canonical_target = self.canonicalize_url(target_url)
        if not canonical_target:
            return None
            
        # Check for existing
        stmt = select(IdentityCrossLinkObservation).where(
            IdentityCrossLinkObservation.source_entity_id == source_entity_id,
            IdentityCrossLinkObservation.target_url_canonical == canonical_target
        )
        result = await self.db.execute(stmt)
        existing = result.scalars().first()
        
        if existing:
            # Update provenance or observed_at
            existing.observed_at = datetime.now(timezone.utc)
            if provenance:
                existing.provenance = provenance
            await self.db.flush()
            return existing
            
        obs = IdentityCrossLinkObservation(
            user_id=user_id,
            source_entity_id=source_entity_id,
            source_entity_type=source_entity_type,
            target_url_canonical=canonical_target,
            direction="outbound",
            observation_source=observation_source,
            provenance=provenance
        )
        self.db.add(obs)
        await self.db.flush()
        return obs

    async def get_observations_for_entity(self, entity_id: uuid.UUID) -> Sequence[IdentityCrossLinkObservation]:
        stmt = select(IdentityCrossLinkObservation).where(
            IdentityCrossLinkObservation.source_entity_id == entity_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
