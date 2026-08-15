"""Load versioned score / linkage catalogs from shared/score_model."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _load_json(path: str) -> dict[str, Any]:
    p = Path(path)
    # try relative to cwd and /app
    candidates = [p, Path("/app") / p, Path("/app/shared") / p.name, Path("shared/score_model") / p.name]
    for c in candidates:
        if c.exists():
            with c.open("r", encoding="utf-8") as f:
                return json.load(f)
    # embedded minimal fallback
    return {
        "model_version": "pdss-v1.0.0-fallback",
        "kind_base_weights": {
            "breach": {"sensitivity": 0.75, "discoverability": 0.85, "linkability": 0.7, "impact": 0.8},
            "other": {"sensitivity": 0.3, "discoverability": 0.5, "linkability": 0.4, "impact": 0.3},
        },
        "severity_bands": {
            "none": [0.0, 0.0],
            "low": [0.1, 3.9],
            "medium": [4.0, 6.9],
            "high": [7.0, 8.9],
            "critical": [9.0, 10.0],
        },
        "aggregation": {"confirmed_weight": 1.0, "possible_weight": 0.55, "diminishing_k": 0.65},
        "surprisal": {"base": 2.0, "scale": 1.35, "cap_contribution": 4.5},
        "temporal": {"recency_half_life_days": 730, "min_recency_factor": 0.55},
        "environmental": {"identifier_type_criticality": {"email": 1.0}},
        "layer_multipliers": {"surface": 1.0},
        "exposed_data_boosts": {"passwords": 0.25},
        "password_risk_map": {},
        "risk_label_map": {},
    }


@lru_cache
def get_pdss_catalog() -> dict[str, Any]:
    settings = get_settings()
    return _load_json(settings.pdss_catalog_path)


@lru_cache
def get_linkage_weights() -> dict[str, Any]:
    settings = get_settings()
    data = _load_json(settings.deciban_weights_path)
    if "prior_match_prob" not in data:
        data = {
            "prior_match_prob": 0.02,
            "comparisons": data.get("comparisons", {}),
            "model_version": data.get("model_version", "linkage-v1.0.0"),
        }
    return data

@lru_cache
def get_recommendation_catalog() -> dict[str, Any]:
    settings = get_settings()
    return _load_json(settings.recommendation_catalog_path)
