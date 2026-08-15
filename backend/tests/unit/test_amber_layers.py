import pytest

from app.domain.amber_layers import (
    AmberPolicyError,
    ExposureLayer,
    consent_purpose_for_layer,
    layer_matches_connector,
    validate_layer_scope,
)


def test_surface_has_no_extra_consent():
    assert consent_purpose_for_layer(ExposureLayer.SURFACE) is None


def test_deep_requires_consent():
    assert (
        consent_purpose_for_layer(ExposureLayer.DEEP)
        == "discovery.deep"
    )


def test_constrained_dark_requires_consent():
    assert (
        consent_purpose_for_layer(ExposureLayer.CONSTRAINED_DARK)
        == "discovery.constrained_dark"
    )


def test_deep_disabled():
    with pytest.raises(AmberPolicyError):
        validate_layer_scope(
            "deep",
            feature_deep_amber=False,
            feature_constrained_dark=False,
        )


def test_constrained_dark_disabled():
    with pytest.raises(AmberPolicyError):
        validate_layer_scope(
            "constrained_dark",
            feature_deep_amber=True,
            feature_constrained_dark=False,
        )


def test_layer_matches_connector():
    assert layer_matches_connector("deep", "deep") is True
    assert layer_matches_connector("deep", "surface") is False
