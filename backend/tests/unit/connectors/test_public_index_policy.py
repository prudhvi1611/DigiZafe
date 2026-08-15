import pytest

from app.connectors.impl.dark_constrained.public_index import (
    append_query,
    parse_public_index_payload,
    validate_public_index_endpoint,
)
from app.security.egress import EgressBlockedError


def test_public_index_requires_https():
    with pytest.raises(EgressBlockedError):
        validate_public_index_endpoint(
            "http://index.example/search",
            {"index.example"},
        )


def test_public_index_rejects_onion():
    with pytest.raises(EgressBlockedError):
        validate_public_index_endpoint(
            "https://example.onion/search",
            {"example.onion"},
        )


def test_public_index_requires_allowlist():
    with pytest.raises(EgressBlockedError):
        validate_public_index_endpoint(
            "https://index.example/search",
            set(),
        )


def test_public_index_allowlisted():
    host, endpoint = validate_public_index_endpoint(
        "https://index.example/search",
        {"index.example"},
    )

    assert host == "index.example"
    assert endpoint.startswith("https://")


def test_append_query():
    result = append_query(
        "https://index.example/search?format=json",
        "q",
        "alice",
    )

    assert "format=json" in result
    assert "q=alice" in result


def test_parse_public_index_payload():
    payload = {
        "results": [
            {"id": "1", "type": "metadata"},
            {"id": "2", "type": "metadata"},
        ]
    }

    rows = parse_public_index_payload(payload, max_results=10)

    assert len(rows) == 2
