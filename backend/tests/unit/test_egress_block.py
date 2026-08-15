import pytest
from app.security.egress import resolve_host, EgressBlockedError, EgressFetcher, EgressError


def test_blocks_localhost_literal():
    f = EgressFetcher()
    with pytest.raises(EgressBlockedError):
        f._validate_url("http://127.0.0.1/")


def test_blocks_metadata_host_resolve(monkeypatch):
    # resolve_host should block 169.254.169.254 if somehow returned
    import app.security.egress as eg

    def fake_getaddrinfo(host, *a, **k):
        return [(None, None, None, None, ("169.254.169.254", 0))]

    monkeypatch.setattr(eg.socket, "getaddrinfo", fake_getaddrinfo)
    with pytest.raises(EgressBlockedError):
        resolve_host("evil.example")


def test_scheme_file_blocked():
    f = EgressFetcher()
    with pytest.raises(EgressBlockedError):
        f._validate_url("file:///etc/passwd")
