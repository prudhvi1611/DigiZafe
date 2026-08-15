from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResidualFeatureContext:
    """The raw approved deterministic inputs used for feature extraction."""
    pdss_score_confirmed: float
    pdss_score_possible: float
    findings: list[Any] = field(default_factory=list)
    # Could include other safe deterministic aggregates here

@dataclass
class ResidualFeatureVector:
    """The flat dictionary of extracted features passed to the model."""
    schema_version: str
    features: dict[str, float]

@dataclass
class ResidualModelMetadata:
    """Registry entry for an approved ML model."""
    version: str
    schema_version: str
    checksum_sha256: str
    timeout_ms: int = 250

@dataclass
class ResidualInference:
    """The result of residual ML evaluation."""
    status: str
    model_version: str | None = None
    feature_schema_version: str | None = None
    raw_delta: float | None = None
    bounded_delta: float | None = None
    confidence: float | None = None
    abstained: bool = False
    reason: str | None = None
