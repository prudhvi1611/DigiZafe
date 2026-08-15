from app.domain.findings_normalize import normalize_observation, normalize_connector_result_observations


def test_xposedornot_breach_normalize():
    obs = {
        "kind": "breach",
        "source": "xposedornot",
        "title": "Breach: Adobe",
        "summary": "Email reported in breach dataset 'Adobe' via XposedOrNot free check.",
        "confidence": 0.85,
        "layer": "surface",
        "raw_ref": "Adobe",
        "attributes": {
            "breach_name": "Adobe",
            "provider": "xposedornot",
            "xposed_data": "Email addresses;Passwords",
            "password_risk": "hardtocrack",
        },
        "attribution": "Data: XposedOrNot",
    }
    nf = normalize_observation(obs)
    assert nf.source == "xposedornot"
    assert nf.kind == "breach"
    assert nf.raw_ref == "Adobe"
    assert nf.fingerprint
    assert nf.severity_hint in {"low", "medium", "high", "critical"}
    assert nf.attribution


def test_dedupe_fingerprints():
    obs = [
        {
            "kind": "breach",
            "source": "xposedornot",
            "title": "Breach: Adobe",
            "summary": "a",
            "confidence": 0.9,
            "raw_ref": "Adobe",
            "attributes": {"breach_name": "Adobe"},
        },
        {
            "kind": "breach",
            "source": "xposedornot",
            "title": "Breach: Adobe",
            "summary": "b",
            "confidence": 0.9,
            "raw_ref": "Adobe",
            "attributes": {"breach_name": "Adobe"},
        },
    ]
    out = normalize_connector_result_observations(obs)
    assert len(out) == 1

def test_archived_metadata_is_possible_and_deep():
    from app.domain.findings_normalize import normalize_observation

    finding = normalize_observation(
        {
            "kind": "archived_metadata",
            "source": "common_crawl",
            "title": "Archived URL metadata match",
            "summary": "Historical URL index metadata",
            "confidence": 0.45,
            "layer": "deep",
            "raw_ref": "https://example.com/archive",
            "attributes": {
                "metadata_only": True,
                "current_exposure_unproven": True,
            },
        }
    )

    assert finding.layer == "deep"
    assert finding.track == "possible"
    assert finding.severity_hint == "info"


def test_public_index_signal_is_metadata_only():
    from app.domain.findings_normalize import normalize_observation

    finding = normalize_observation(
        {
            "kind": "public_index_signal",
            "source": "public_index",
            "title": "Configured public-index metadata match",
            "summary": "Metadata only",
            "confidence": 0.35,
            "layer": "constrained_dark",
            "attributes": {
                "metadata_only": True,
                "raw_content_retrieved": False,
            },
        }
    )

    assert finding.layer == "constrained_dark"
    assert finding.track == "possible"
    assert finding.attributes["metadata_only"] is True

