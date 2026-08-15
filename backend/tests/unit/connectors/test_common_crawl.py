from app.connectors.impl.deep.common_crawl import (
    build_common_crawl_pattern,
    parse_cdx_json_lines,
)


def test_domain_pattern():
    assert build_common_crawl_pattern(
        "domain",
        "example.com",
    ) == "*.example.com/*"


def test_username_pattern():
    assert build_common_crawl_pattern(
        "username",
        "alice",
    ) == "*alice*"


def test_email_is_not_sent_to_archive_adapter():
    try:
        build_common_crawl_pattern("email", "alice@example.com")
    except ValueError as exc:
        assert "supports" in str(exc).lower()
    else:
        raise AssertionError("Email should not be supported by Common Crawl adapter")


def test_parse_cdx_json_lines():
    body = (
        b'{"url":"https://example.com/a","status":"200"}\n'
        b'not-json\n'
        b'{"url":"https://example.com/b","status":"200"}\n'
    )

    rows = parse_cdx_json_lines(body, max_results=10)

    assert len(rows) == 2
    assert rows[0]["url"] == "https://example.com/a"
