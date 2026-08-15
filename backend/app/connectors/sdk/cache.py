"""JSON cache over Redis (cache instance, allkeys-lru)."""
from __future__ import annotations

import hashlib
import json
from typing import Any

import redis.asyncio as redis

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorCache:
    def __init__(self, redis_client: redis.Redis, prefix: str = "ccache") -> None:
        self.redis = redis_client
        self.prefix = prefix

    def make_key(self, connector_id: str, *parts: str) -> str:
        raw = "|".join([connector_id, *parts])
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]
        return f"{self.prefix}:{connector_id}:{h}"

    async def get_json(self, key: str) -> Any | None:
        try:
            data = await self.redis.get(key)
            if data is None:
                return None
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return json.loads(data)
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> None:
        try:
            payload = json.dumps(value, default=str)
            await self.redis.set(key, payload, ex=max(1, ttl_seconds))
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))
