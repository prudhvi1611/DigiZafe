import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "DigiZafe"
        assert "health" in data


@pytest.mark.asyncio
async def test_health_endpoint_exists():
    # Note: full DB test requires running postgres; this checks the route is mounted
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Will fail on DB if no real connection, but route exists
        resp = await client.get("/api/v1/health/ready")
        assert resp.status_code in (200, 503)
        # In a test without real redis/postgres, it will return unready, which means the endpoint is mounted correctly.
        assert resp.json()["status"] in ["ready", "unready"]
