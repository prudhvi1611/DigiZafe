import hashlib
import os
import sys

import structlog

from app.core.config import get_settings
from app.ml.registry import get_model_metadata

logger = structlog.get_logger(__name__)


def validate_production_config() -> None:
    """
    Validates that the production configuration is safe.
    Fails closed (sys.exit(1)) if critical safety constraints are violated.
    """
    settings = get_settings()

    if settings.app_env.lower() == "production":
        # 1. Environment & Debug
        if settings.debug:
            logger.error("startup_validation_failed", reason="DEBUG mode is enabled in production environment.")
            sys.exit(1)

        # 2. Secret Key
        if len(settings.secret_key) < 32:
            logger.error("startup_validation_failed", reason="secret_key is too short for production.")
            sys.exit(1)

        # 3. CORS
        if "*" in settings.cors_origins:
            logger.error("startup_validation_failed", reason="Wildcard CORS origins are not allowed in production.")
            sys.exit(1)

    # 4. Optional Residual ML Validation
    if settings.feature_ml_residual:
        metadata = get_model_metadata(settings.residual_ml_model_version)
        if not metadata:
            logger.error(
                "startup_validation_failed", 
                reason="Residual ML is enabled but no trusted metadata exists for configured version.",
                version=settings.residual_ml_model_version
            )
            sys.exit(1)

        if not os.path.exists(settings.residual_ml_model_path):
            logger.error(
                "startup_validation_failed",
                reason="Residual ML is enabled but the model artifact is missing.",
                path=settings.residual_ml_model_path
            )
            sys.exit(1)

        # Verify SHA-256 Checksum
        sha256_hash = hashlib.sha256()
        with open(settings.residual_ml_model_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        actual_checksum = sha256_hash.hexdigest()
        if actual_checksum != metadata.checksum_sha256:
            logger.error(
                "startup_validation_failed",
                reason="Residual ML artifact checksum mismatch! Artifact may be corrupted or tampered with.",
                expected_checksum=metadata.checksum_sha256,
                actual_checksum=actual_checksum
            )
            sys.exit(1)
            
        if metadata.schema_version != settings.residual_ml_feature_schema_version:
            logger.error(
                "startup_validation_failed",
                reason="Residual ML feature schema mismatch.",
                expected_schema=metadata.schema_version,
                configured_schema=settings.residual_ml_feature_schema_version
            )
            sys.exit(1)

    # 5. Narrative Provider Validation
    if settings.feature_grounded_narrative and settings.narrative_enabled:
        if not settings.groq_api_key:
            logger.warning(
                "startup_validation_warning",
                reason="Grounded narrative is enabled but groq_api_key is missing. Will fall back to deterministic narratives."
            )

    logger.info("startup_validation_passed", env=settings.app_env)
