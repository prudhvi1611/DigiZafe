"""Async Redis clients for broker vs cache (Sprint 0 split)."""
from __future__ import annotations

import redis.asyncio as redis

from app.core.config import get_settings

_cache: redis.Redis | None = None
_broker: redis.Redis | None = None


async def get_cache_redis() -> redis.Redis:
    global _cache
    if _cache is None:
        settings = get_settings()
        _cache = redis.from_url(settings.redis_cache_url, decode_responses=True)
    return _cache


async def get_broker_redis() -> redis.Redis:
    global _broker
    if _broker is None:
        settings = get_settings()
        _broker = redis.from_url(settings.redis_broker_url, decode_responses=True)
    return _broker
