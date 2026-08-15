from app.connectors.sdk.types import LegalityTier, ObservationKind


def test_enums():
    assert LegalityTier.GREEN.value == "green"
    assert ObservationKind.BREACH.value == "breach"
