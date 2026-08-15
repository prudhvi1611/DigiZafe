"""Canonical ordered feature schema for Sprint 12 Residual ML."""

RESIDUAL_FEATURES_V1 = [
    # Finding counts by kind
    "count_finding_credential",
    "count_finding_identity",
    "count_finding_financial",
    
    # Finding track counts
    "count_track_confirmed",
    "count_track_possible",
    
    # Severity aggregations (base)
    "sum_base_severity",
    "max_base_severity",
    
    # Provenance metrics
    "source_diversity",  # unique sources
    "avg_confidence",
    
    # Sub-scores
    "pdss_score_confirmed",
    "pdss_score_possible",
]

SCHEMA_VERSION = "residual-features-v1"
