from app.domain.remediation_profile import build_profile_from_identifiers


def test_only_verified_email():
    p = build_profile_from_identifiers(
        [
            {"type": "email", "value_canonical": "a@b.com", "is_verified": True},
            {"type": "email", "value_canonical": "x@y.com", "is_verified": False},
        ],
        display_name="Jane Doe",
        state="CA",
    )
    assert p.email == "a@b.com"
    assert p.first_name == "Jane"
    assert p.state == "CA"
