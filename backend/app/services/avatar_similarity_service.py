import hashlib
import io
import logging
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from PIL import Image
import imagehash
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.models.profile_visual_fingerprint import ProfileVisualFingerprint
from app.security.egress import get_egress_fetcher, EgressError, EgressResponse

logger = logging.getLogger(__name__)

# Pillow decompression bomb protection
Image.MAX_IMAGE_PIXELS = None  # We will enforce strictly at application level

class AvatarSafetyError(Exception):
    pass

class AvatarSimilarityService:
    """
    Safely retrieves and computes non-biometric visual evidence (exact and perceptual hashes).
    Enforces SSRF boundaries and strict image decode limits.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.fetcher = get_egress_fetcher()
        
        # Explicitly configure Pillow's own bomb limit just in case
        Image.MAX_IMAGE_PIXELS = self.settings.avatar_max_decoded_pixels

    async def _safe_fetch_image(self, url: str) -> bytes:
        # Use existing Egress boundary for SSRF and network timeouts
        try:
            resp: EgressResponse = await self.fetcher.fetch(
                url, 
                method="GET", 
                timeout=self.settings.avatar_network_timeout_seconds,
                purpose="avatar_enrichment"
            )
        except EgressError as e:
            raise AvatarSafetyError(f"Egress fetch failed: {e}")
            
        if resp.status_code != 200:
            raise AvatarSafetyError(f"HTTP status {resp.status_code}")
            
        content_type = resp.headers.get("content-type", "").lower()
        # Optional: check headers, but we strictly validate via Pillow
        
        # Limit bytes is already enforced by egress_max_response_bytes, but we 
        # can enforce avatar specific limits
        if len(resp.body) > self.settings.avatar_max_download_bytes:
            raise AvatarSafetyError(f"Image exceeds max size {self.settings.avatar_max_download_bytes}")
            
        return resp.body

    def _process_image(self, body: bytes) -> dict:
        try:
            with Image.open(io.BytesIO(body)) as img:
                # Force load to catch malformed files and truncation
                img.verify()
                
            # verify() leaves the file pointer at the end. We need to reopen to process.
            with Image.open(io.BytesIO(body)) as img:
                fmt = img.format.lower()
                mime = f"image/{fmt}"
                if mime not in self.settings.avatar_supported_mime_types:
                    raise AvatarSafetyError(f"Unsupported image format: {fmt}")
                    
                width, height = img.size
                if width > self.settings.avatar_max_width or height > self.settings.avatar_max_height:
                    raise AvatarSafetyError(f"Image dimensions exceed max ({width}x{height})")
                    
                if width * height > self.settings.avatar_max_decoded_pixels:
                    raise AvatarSafetyError("Image pixel count exceeds maximum limit")
                    
                # Exact Hash
                exact_hash = hashlib.sha256(body).hexdigest()
                
                # Perceptual Hash (convert to RGB/grayscale for consistent phash)
                try:
                    phash = str(imagehash.phash(img))
                except Exception as e:
                    logger.warning("phash_calculation_failed", error=str(e))
                    phash = None
                    
                return {
                    "mime_type": mime,
                    "width": width,
                    "height": height,
                    "exact_hash_sha256": exact_hash,
                    "phash": phash,
                }
        except AvatarSafetyError:
            raise
        except Exception as e:
            raise AvatarSafetyError(f"Image processing failed: {e}")

    async def fetch_and_fingerprint(
        self, 
        user_id: uuid.UUID, 
        candidate_id: uuid.UUID | None, 
        confirmed_profile_id: uuid.UUID | None,
        source_url: str,
        provenance: dict
    ) -> ProfileVisualFingerprint | None:
        """
        Safely fetch an avatar image, compute non-biometric visual hashes, and store/return the fingerprint.
        """
        if not self.settings.feature_avatar_similarity:
            logger.info("avatar_similarity_disabled")
            return None
            
        canonical_url = source_url.strip()
        
        try:
            body = await self._safe_fetch_image(canonical_url)
            # Run CPU bound image processing in thread
            import asyncio
            result = await asyncio.to_thread(self._process_image, body)
            
            fingerprint = ProfileVisualFingerprint(
                user_id=user_id,
                candidate_id=candidate_id,
                confirmed_profile_id=confirmed_profile_id,
                exact_hash_sha256=result["exact_hash_sha256"],
                phash=result["phash"],
                mime_type=result["mime_type"],
                width=result["width"],
                height=result["height"],
                source_url_canonical=canonical_url,
                source_provenance=provenance,
                observed_at=datetime.now(timezone.utc),
                status="active"
            )
            self.db.add(fingerprint)
            await self.db.flush()
            return fingerprint
            
        except AvatarSafetyError as e:
            logger.warning("avatar_fetch_failed", url=canonical_url, error=str(e))
            return None
            
    def compute_distance(self, phash1: str, phash2: str) -> int:
        """Compute hamming distance between two hex string pHashes."""
        try:
            h1 = imagehash.hex_to_hash(phash1)
            h2 = imagehash.hex_to_hash(phash2)
            return h1 - h2
        except Exception:
            return 999
