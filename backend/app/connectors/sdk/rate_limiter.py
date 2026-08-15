"""Redis token-bucket / fixed-window hybrid rate limiter for free APIs."""
from __future__ import annotations

import time

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimitExceeded(Exception):
    def __init__(self, key: str, retry_after: float | None = None) -> None:
        super().__init__(f"Rate limit exceeded: {key}")
        self.key = key
        self.retry_after = retry_after


class RateLimiter:
    """
    Multi-window limiter using Redis INCR + EXPIRE.
    Windows: second, hour, day (optional).
    """

    def __init__(self, redis_client: redis.Redis, prefix: str = "rl") -> None:
        self.redis = redis_client
        self.prefix = prefix

    def _k(self, *parts: str) -> str:
        return ":".join([self.prefix, *parts])

    async def acquire(
        self,
        name: str,
        *,
        per_second: float | None = None,
        per_hour: int | None = None,
        per_day: int | None = None,
    ) -> None:
        now = time.time()
        # Second window (ceil to int capacity)
        if per_second is not None and per_second > 0:
            cap = max(1, int(per_second)) if per_second >= 1 else 1
            # For sub-1/sec use millisecond-ish: allow 1 then sleep externally — enforce min interval via second key with TTL 1
            key = self._k(name, "s", str(int(now)))
            n = await self.redis.incr(key)
            if n == 1:
                await self.redis.expire(key, 2)
            # If rate < 1/sec, treat as max 1 per second
            limit = max(1, int(per_second)) if per_second >= 1 else 1
            if n > limit:
                raise RateLimitExceeded(name, retry_after=1.0)

        if per_hour is not None and per_hour > 0:
            hour_bucket = time.strftime("%Y%m%d%H", time.gmtime(now))
            key = self._k(name, "h", hour_bucket)
            n = await self.redis.incr(key)
            if n == 1:
                await self.redis.expire(key, 3700)
            if n > per_hour:
                raise RateLimitExceeded(name, retry_after=300.0)

        if per_day is not None and per_day > 0:
            day_bucket = time.strftime("%Y%m%d", time.gmtime(now))
            key = self._k(name, "d", day_bucket)
            n = await self.redis.incr(key)
            if n == 1:
                await self.redis.expire(key, 90000)
            if n > per_day:
                raise RateLimitExceeded(name, retry_after=3600.0)

    async def acquire_user_quota(self, user_id: str, *, limit: int | None = None) -> None:
        settings = get_settings()
        limit = limit if limit is not None else settings.connector_per_user_probe_quota_per_day
        day_bucket = time.strftime("%Y%m%d", time.gmtime())
        key = self._k("user_probe", user_id, day_bucket)
        n = await self.redis.incr(key)
        if n == 1:
            await self.redis.expire(key, 90000)
        if n > limit:
            raise RateLimitExceeded(f"user_probe:{user_id}", retry_after=3600.0)
