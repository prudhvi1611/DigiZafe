from app.ml.contracts import ResidualModelMetadata

RESIDUAL_REGISTRY = {
    "residual-risk-v1": ResidualModelMetadata(
        version="residual-risk-v1",
        schema_version="residual-features-v1",
        # We will populate the real checksum after training. 
        # For now, it will be updated during the training pipeline run.
        checksum_sha256="f50a34698f657c40ba2aced39a7baa440155573e122692e80ec688c223737e22",
        timeout_ms=250
    )
}

def get_model_metadata(version: str) -> ResidualModelMetadata | None:
    return RESIDUAL_REGISTRY.get(version)
