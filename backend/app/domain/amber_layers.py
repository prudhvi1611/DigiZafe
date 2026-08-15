"""Pure Amber layer policy helpers."""
from __future__ import annotations

from typing import Any

from app.domain.exposure_layers import ExposureLayer


class AmberPolicyError(ValueError):
    pass


LAYER_CONSENT_PURPOSE: dict[ExposureLayer, str | None] = {
    ExposureLayer.SURFACE: None,
    ExposureLayer.DEEP: "discovery.deep",
    ExposureLayer.CONSTRAINED_DARK: "discovery.constrained_dark",
}


LAYER_COPY: dict[ExposureLayer, dict[str, str]] = {
    ExposureLayer.SURFACE: {
        "label": "Surface",
        "description": "Public surface-web connectors and free breach metadata.",
        "warning": "Standard surface discovery.",
    },
    ExposureLayer.DEEP: {
        "label": "Deep",
        "description": "Public archive and index metadata that is not part of the ordinary live surface scan.",
        "warning": "Historical or indexed metadata may be incomplete or stale.",
    },
    ExposureLayer.CONSTRAINED_DARK: {
        "label": "Constrained-Dark",
        "description": "Operator-approved public index metadata only.",
        "warning": (
            "This is not unrestricted dark-web crawling. No Tor access, marketplace access, "
            "credentialed access, or raw dump retrieval is permitted."
        ),
    },
}


def parse_layer(value: ExposureLayer | str) -> ExposureLayer:
    try:
        return value if isinstance(value, ExposureLayer) else ExposureLayer(value)
    except ValueError as exc:
        raise AmberPolicyError(f"Unsupported exposure layer: {value}") from exc


def consent_purpose_for_layer(value: ExposureLayer | str) -> str | None:
    return LAYER_CONSENT_PURPOSE[parse_layer(value)]


def is_amber_layer(value: ExposureLayer | str) -> bool:
    return parse_layer(value) != ExposureLayer.SURFACE


def layer_matches_connector(
    requested_layer: ExposureLayer | str,
    connector_layer: str,
) -> bool:
    requested = parse_layer(requested_layer)
    return requested.value == connector_layer


def validate_layer_scope(
    value: ExposureLayer | str,
    *,
    feature_deep_amber: bool,
    feature_constrained_dark: bool,
) -> ExposureLayer:
    layer = parse_layer(value)

    if layer == ExposureLayer.DEEP and not feature_deep_amber:
        raise AmberPolicyError("Deep Amber discovery is disabled")

    if layer == ExposureLayer.CONSTRAINED_DARK and not feature_constrained_dark:
        raise AmberPolicyError("Constrained-Dark discovery is disabled")

    return layer


def public_layer_metadata(value: ExposureLayer | str) -> dict[str, Any]:
    layer = parse_layer(value)
    return {
        "layer": layer.value,
        **LAYER_COPY[layer],
        "requires_explicit_consent": is_amber_layer(layer),
    }
