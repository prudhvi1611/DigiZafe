from app.domain.privacy_export import build_export_package


def test_export_shape():
    pkg = build_export_package(
        user={"id": "u1", "email": "a@b.com", "is_active": True, "mfa_enabled": False,
              "created_at": None, "last_login_at": None},
        identifiers=[{"type": "email", "value_canonical": "a@b.com"}],
        findings=[],
        scores=[],
        recommendations=[],
        remediation_state=[],
        consent_records=[{"purpose": "discovery.xposedornot", "granted": True}],
    )
    assert pkg["export_version"] == "1.0.0"
    assert pkg["subject"]["email"] == "a@b.com"
    assert "rights" in pkg
