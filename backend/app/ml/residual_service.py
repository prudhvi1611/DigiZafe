import sys

sys.path.insert(0, "/home/digizafe/.local/lib/python3.12/site-packages")
import pandas as pd
import structlog

from app.core.config import get_settings

settings = get_settings()
from app.ml.contracts import ResidualFeatureContext, ResidualInference
from app.ml.feature_adapter import extract_features
from app.ml.model_loader import load_verified_model
from app.ml.registry import get_model_metadata

logger = structlog.get_logger(__name__)

# Cache for the loaded model in memory
_MODEL_CACHE = None
_MODEL_VERSION_CACHED = None

def evaluate_residual(ctx: ResidualFeatureContext) -> ResidualInference:
    """
    Evaluates the residual ML risk signal. 
    Returns abstained or unavailable if anything goes wrong.
    """
    if not settings.feature_residual_ml:
        return ResidualInference(status="disabled")
        
    metadata = get_model_metadata(settings.residual_ml_model_version)
    if not metadata:
        return ResidualInference(status="unavailable", reason="model_not_in_registry")
        
    global _MODEL_CACHE, _MODEL_VERSION_CACHED
    if settings.residual_ml_model_version != _MODEL_VERSION_CACHED or _MODEL_CACHE is None:
        _MODEL_CACHE = load_verified_model(settings.residual_ml_model_path, metadata)
        _MODEL_VERSION_CACHED = settings.residual_ml_model_version
        
    if _MODEL_CACHE is None:
        return ResidualInference(status="unavailable", reason="model_load_failed")
        
    try:
        # Extract features
        vector = extract_features(ctx)
        
        # Verify schema match
        if vector.schema_version != settings.residual_ml_feature_schema_version or vector.schema_version != metadata.schema_version:
            return ResidualInference(
                status="abstained", 
                reason="schema_version_mismatch",
                model_version=metadata.version,
                feature_schema_version=vector.schema_version
            )
            
        # Convert dictionary to DataFrame for sklearn prediction (maintain exact column order)
        import sys
        sys.path.append("/app/ml/features") # Make sure backend can resolve this if needed
        from app.ml.residual_features import RESIDUAL_FEATURES_V1
        
        # The model expects an array with exact column ordering
        # Ensure we have all features and no extras
        row = []
        for feature_name in RESIDUAL_FEATURES_V1:
            if feature_name not in vector.features:
                return ResidualInference(
                    status="abstained",
                    reason=f"missing_feature_{feature_name}",
                    model_version=metadata.version,
                    feature_schema_version=vector.schema_version
                )
            row.append(vector.features[feature_name])
            
        df = pd.DataFrame([row], columns=RESIDUAL_FEATURES_V1)
        
        # NOTE: scikit-learn predictions are synchronous and fast for HistGradientBoostingRegressor. 
        # A true hard-timeout would require a separate process. We rely on the model being small 
        # and bounded in dimension. 
        raw_delta = _MODEL_CACHE.predict(df)[0]
        
        # Bound the output
        max_delta = settings.residual_ml_max_abs_delta
        bounded_delta = max(-max_delta, min(max_delta, raw_delta))
        
        return ResidualInference(
            status="evaluated",
            model_version=metadata.version,
            feature_schema_version=vector.schema_version,
            raw_delta=float(raw_delta),
            bounded_delta=float(bounded_delta),
            confidence=None, # HistGradientBoostingRegressor does not provide per-prediction confidence
            abstained=False,
            reason=None
        )
        
    except Exception as e:
        logger.error("residual_ml_inference_error", error=str(e))
        return ResidualInference(
            status="abstained", 
            reason="inference_error",
            model_version=metadata.version
        )
