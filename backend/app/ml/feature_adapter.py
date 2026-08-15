import os
import sys

# Add ml features path to import RESIDUAL_FEATURES_V1
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))
from app.ml.contracts import ResidualFeatureContext, ResidualFeatureVector
from ml.features.residual_features import RESIDUAL_FEATURES_V1, SCHEMA_VERSION

# Standard severity mapping if severity isn't already a float
SEVERITY_MAP = {
    "critical": 10.0,
    "high": 8.0,
    "medium": 5.0,
    "low": 2.0,
    "none": 0.0
}

def extract_features(ctx: ResidualFeatureContext) -> ResidualFeatureVector:
    """Deterministically maps a context into a flat feature dictionary."""
    features = {f: 0.0 for f in RESIDUAL_FEATURES_V1}
    
    # Sub-scores
    features["pdss_score_confirmed"] = float(ctx.pdss_score_confirmed)
    features["pdss_score_possible"] = float(ctx.pdss_score_possible)
    
    unique_sources = set()
    total_confidence = 0.0
    valid_confidences = 0
    
    sum_base_severity = 0.0
    max_base_severity = 0.0
    
    for finding in ctx.findings:
        # Assuming finding is either FindingScoreInput or a dict
        # If it's a dict (e.g. from DB JSON), we access via keys
        is_dict = isinstance(finding, dict)
        
        kind = finding.get("kind", "") if is_dict else getattr(finding, "kind", "")
        track = finding.get("track", "") if is_dict else getattr(finding, "track", "")
        source = finding.get("source", "") if is_dict else getattr(finding, "source", "")
        confidence = finding.get("confidence", 0.0) if is_dict else getattr(finding, "confidence", 0.0)
        severity_hint = finding.get("severity_hint", "none") if is_dict else getattr(finding, "severity_hint", "none")
        
        # Counts by kind
        if kind == "credential":
            features["count_finding_credential"] += 1.0
        elif kind == "identity":
            features["count_finding_identity"] += 1.0
        elif kind == "financial":
            features["count_finding_financial"] += 1.0
            
        # Track counts
        if track == "confirmed":
            features["count_track_confirmed"] += 1.0
        elif track == "possible":
            features["count_track_possible"] += 1.0
            
        # Sources
        if source:
            unique_sources.add(source)
            
        # Confidence
        if confidence is not None:
            total_confidence += float(confidence)
            valid_confidences += 1
            
        # Severity
        sev_val = SEVERITY_MAP.get(severity_hint.lower(), 0.0)
        sum_base_severity += sev_val
        if sev_val > max_base_severity:
            max_base_severity = sev_val
            
    features["sum_base_severity"] = sum_base_severity
    features["max_base_severity"] = max_base_severity
    features["source_diversity"] = float(len(unique_sources))
    features["avg_confidence"] = float(total_confidence / valid_confidences) if valid_confidences > 0 else 0.0
    
    return ResidualFeatureVector(
        schema_version=SCHEMA_VERSION,
        features=features
    )
