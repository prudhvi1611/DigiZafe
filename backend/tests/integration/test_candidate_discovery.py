import pytest
import uuid
from httpx import AsyncClient
from app.connectors.maigret_adapter import MaigretAdapter, is_safe_username
from app.models.identity_anchor import IdentityAnchor, IdentityAlias
from app.models.candidate_profile import CandidateDiscoveryRun, CandidateProfile

@pytest.fixture
async def discovery_feature_flag(monkeypatch):
    from app.core.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "feature_connector_orchestration", True)
    return settings

@pytest.fixture
async def async_client(db_session):
    from app.main import app
    from httpx import ASGITransport
    from app.api.deps import get_db

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()

@pytest.fixture
async def user_id(db_session):
    from app.models.user import User
    from app.security.password import hash_password
    user = User(email=f"test_{uuid.uuid4()}@example.com", hashed_password=hash_password("SecurePassword123!"))
    db_session.add(user)
    await db_session.commit()
    return user.id

@pytest.fixture
async def token_headers(user_id):
    from app.security.jwt import create_access_token
    token = create_access_token(str(user_id))
    return {"Authorization": f"Bearer {token}"}

@pytest.mark.asyncio
async def test_maigret_adapter_command_injection():
    adapter = MaigretAdapter()
    
    # Valid username
    assert is_safe_username("pranav") == True
    
    # Injection attempts
    assert is_safe_username("pranav; cat /etc/passwd") == False
    assert is_safe_username("pranav|ls") == False
    assert is_safe_username("pranav&whoami") == False
    assert is_safe_username("pranav > file") == False
    assert is_safe_username("pranav`") == False
    assert is_safe_username("pranav$") == False
    assert is_safe_username("pranav\nls") == False
    
    # Should safely return error
    res = adapter.run_discovery("pranav; ls")
    assert res["error"] == "invalid_input"

@pytest.mark.asyncio
async def test_feature_flag_disabled(async_client: AsyncClient, token_headers, db_session):
    # Default is disabled without the fixture
    res = await async_client.post("/api/v1/identity/discovery/orchestrate", headers=token_headers, json={"identity_input_ids": []})
    assert res.status_code == 403
    assert "disabled" in res.json()["detail"]

@pytest.mark.asyncio
async def test_start_discovery_no_consent(async_client: AsyncClient, token_headers, db_session, discovery_feature_flag, user_id):
    # Assuming the test user has no consent
    anchor = IdentityAnchor(user_id=user_id, status="active", version=1)
    db_session.add(anchor)
    await db_session.commit()
    
    res = await async_client.post("/api/v1/identity/discovery/orchestrate", headers=token_headers, json={"identity_input_ids": []})
    assert res.status_code == 400
    assert "No eligible inputs" in res.json()["detail"]

# Need to implement the rest of RLS, deduplication and adapter failure tests.
