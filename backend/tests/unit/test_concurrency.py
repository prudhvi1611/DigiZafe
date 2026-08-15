import pytest
from unittest.mock import AsyncMock
from app.services.discovery.connector_budget_service import ConnectorBudgetService

@pytest.mark.asyncio
async def test_concurrency_fail_closed():
    # Mock redis client that raises an exception when trying to acquire lease
    redis_client = AsyncMock()
    redis_client.eval.side_effect = Exception("Redis connection failed")
    
    budget = ConnectorBudgetService(redis_client)
    
    # Budget service fails closed and returns False when redis fails
    result = await budget.acquire_connector_lease("test_connector", "test-lease-id")
    assert result is False
