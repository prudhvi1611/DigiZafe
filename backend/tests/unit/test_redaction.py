from app.connectors.maigret_adapter import redact_secrets as maigret_redact
from app.services.discovery.connectors.osintgram_adapter import redact_secrets as osintgram_redact

def test_maigret_redaction():
    text = "Error: Invalid API_KEY=12345-abcde for this user."
    redacted = maigret_redact(text)
    assert "12345-abcde" not in redacted
    assert "API_KEY=***REDACTED***" in redacted

def test_osintgram_redaction():
    text = "Exception: sessionid='xyz123' expired."
    redacted = osintgram_redact(text)
    assert "xyz123" not in redacted
    assert "sessionid=***REDACTED***" in redacted
