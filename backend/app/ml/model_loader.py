import hashlib
import os

import joblib
import structlog

from app.ml.contracts import ResidualModelMetadata

logger = structlog.get_logger(__name__)

def load_verified_model(path: str, metadata: ResidualModelMetadata):
    """
    Loads a joblib model strictly after verifying its SHA-256 checksum.
    Returns the model object if verified, or None if missing/invalid.
    """
    if not os.path.exists(path):
        logger.warning("residual_ml_model_missing", path=path)
        return None

    try:
        # Verify checksum first to prevent executing untrusted joblib code
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
                
        actual_checksum = sha256_hash.hexdigest()
        
        if actual_checksum != metadata.checksum_sha256:
            logger.error(
                "residual_ml_checksum_mismatch", 
                expected=metadata.checksum_sha256, 
                actual=actual_checksum,
                path=path
            )
            return None
            
        # Only load if checksum is exact match
        model = joblib.load(path)
        return model
        
    except Exception as e:
        logger.error("residual_ml_load_error", error=str(e), path=path)
        return None
