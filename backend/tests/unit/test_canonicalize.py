import pytest
from app.domain.canonicalize import (
    canonicalize_email,
    canonicalize_domain,
    canonicalize_phone,
    canonicalize_github_username,
    CanonicalizationError,
    display_redacted,
    IdentifierType,
)


def test_email_gmail_dots_plus():
    assert canonicalize_email("F.O.O+tag@Gmail.com") == "foo@gmail.com"


def test_email_invalid():
    with pytest.raises(CanonicalizationError):
        canonicalize_email("not-an-email")


def test_domain():
    assert canonicalize_domain("https://WWW.Example.COM/path") == "www.example.com"


def test_phone_e164():
    assert canonicalize_phone("+1 (415) 555-2671") == "+14155552671"


def test_github():
    assert canonicalize_github_username("@Octocat") == "octocat"


def test_redact_email():
    r = display_redacted(IdentifierType.EMAIL, "ab@example.com")
    assert "***" in r
