from app.domain.pdss import PDSSEngine, FindingScoreInput
from app.services.catalog_loader import get_pdss_catalog


def test_empty_score():
    eng = PDSSEngine(get_pdss_catalog())
    r = eng.score([])
    assert r.score_combined == 0.0
    assert r.severity in {"none", "low"}


def test_xposedornot_breach_drives_score():
    eng = PDSSEngine(get_pdss_catalog())
    findings = [
        FindingScoreInput(
            id="f1",
            kind="breach",
            source="xposedornot",
            title="Breach: Adobe",
            confidence=0.9,
            layer="surface",
            track="confirmed",
            severity_hint="high",
            raw_ref="Adobe",
            attributes={
                "breach_name": "Adobe",
                "xposed_data": "Email addresses;Passwords",
                "password_risk": "easytocrack",
                "xposed_date": "2013",
                "risk_label": "high",
                "provider": "xposedornot",
            },
            attribution="Data: XposedOrNot",
        ),
        FindingScoreInput(
            id="f2",
            kind="profile",
            source="gravatar",
            title="Gravatar present",
            confidence=0.9,
            layer="surface",
            track="confirmed",
            severity_hint="low",
            raw_ref="gravatar",
            attributes={},
        ),
    ]
    r = eng.score(findings, identifier_type="email", identity_edge_count=1)
    assert r.score_combined > 0
    assert r.contributions
    assert any(c.source == "xposedornot" for c in r.contributions)
    assert "PDSS:" in r.vector
    assert r.counterfactuals
    # what-if remove adobe should lower score
    r2 = eng.score(findings, exclude_finding_ids={"f1"})
    assert r2.score_combined <= r.score_combined
