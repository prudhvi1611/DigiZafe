import pytest
from app.services.discovery.connectors.osintgram_adapter import OSINTgramAdapter
from app.services.discovery.connectors.capability_registry import ConnectorCapability
import os

@pytest.mark.asyncio
async def test_osintgram_adapter_injection(monkeypatch):
    adapter = OSINTgramAdapter()
    
    # Enable feature
    monkeypatch.setattr(adapter.settings, "feature_osintgram_discovery", True)
    monkeypatch.setenv("OSINTGRAM_SESSION_ID", "mock_session")
    
    # 1. Option injection
    res = await adapter.execute("--help", ConnectorCapability.PROFILE_LOOKUP)
    assert res["status"] == "failed"
    assert res["error"] == "invalid_input"
    
    # 2. Command injection
    res = await adapter.execute("test; cat /etc/passwd", ConnectorCapability.PROFILE_LOOKUP)
    assert res["status"] == "failed"
    assert res["error"] == "invalid_input"

@pytest.mark.asyncio
async def test_osintgram_zero_execution(monkeypatch):
    adapter = OSINTgramAdapter()
    
    # 1. Feature disabled
    monkeypatch.setattr(adapter.settings, "feature_osintgram_discovery", False)
    monkeypatch.setenv("OSINTGRAM_SESSION_ID", "mock_session")
    res = await adapter.execute("someuser", ConnectorCapability.PROFILE_LOOKUP)
    assert res["status"] == "failed"
    assert res["error"] == "disabled"
    
    # 2. Secret missing
    monkeypatch.setattr(adapter.settings, "feature_osintgram_discovery", True)
    monkeypatch.delenv("OSINTGRAM_SESSION_ID", raising=False)
    res = await adapter.execute("someuser", ConnectorCapability.PROFILE_LOOKUP)
    assert res["status"] == "failed"
    assert res["error"] == "not_configured"
