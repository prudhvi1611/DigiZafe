import uuid
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectorBudgetService:
    ACQUIRE_SCRIPT = """
    local zset_key = KEYS[1]
    local lease_id = ARGV[1]
    local current_time = tonumber(ARGV[2])
    local expiry_time = tonumber(ARGV[3])
    local max_concurrency = tonumber(ARGV[4])

    redis.call('ZREMRANGEBYSCORE', zset_key, '-inf', current_time)

    local current_count = redis.call('ZCARD', zset_key)
    if current_count >= max_concurrency then
        return 0
    end

    redis.call('ZADD', zset_key, expiry_time, lease_id)
    local ttl = expiry_time - current_time + 60
    redis.call('EXPIRE', zset_key, ttl)

    return 1
    """

    def __init__(self, redis: Redis):
        self.redis = redis
        self.settings = get_settings()
        self._acquire_script = self.redis.register_script(self.ACQUIRE_SCRIPT)

    async def check_and_consume_orchestration_run(self, user_id: uuid.UUID, purpose: str = "general") -> bool:
        """
        Check if the user can perform an orchestration run right now.
        Returns False if budget is exhausted or Redis is unavailable (fail closed).
        """
        try:
            if purpose == "temporal_revalidation":
                hour_key = f"rate_limit:manual_reval:{user_id}:hour"
                day_key = f"rate_limit:manual_reval:{user_id}:day"
                max_hour = self.settings.manual_revalidation_max_runs_per_user_per_hour
                max_day = self.settings.manual_revalidation_max_runs_per_user_per_day
            else:
                hour_key = f"budget:user:{user_id}:hour"
                day_key = f"budget:user:{user_id}:day"
                max_hour = self.settings.orchestration_max_runs_per_user_per_hour
                max_day = self.settings.orchestration_max_runs_per_user_per_day
            
            # Perform optimistic increment
            pipe = self.redis.pipeline()
            pipe.incr(hour_key)
            pipe.expire(hour_key, 3600, nx=True)
            pipe.incr(day_key)
            pipe.expire(day_key, 86400, nx=True)
            results = await pipe.execute()
            
            hour_count = results[0]
            day_count = results[2]
            
            # Check limits
            exceeded = False
            if hour_count > max_hour:
                exceeded = True
            if day_count > max_day:
                exceeded = True
                
            if exceeded:
                # If exceeded, we decrement back as it's not consumed
                pipe = self.redis.pipeline()
                pipe.decr(hour_key)
                pipe.decr(day_key)
                await pipe.execute()
                return False
                
            return True
        except Exception as e:
            logger.error("redis_unavailable", details={"context": "check_and_consume_orchestration_run", "error": str(e)})
            return False

    async def check_active_run_budget(self, user_id: uuid.UUID, current_active: int) -> bool:
        if current_active >= self.settings.orchestration_max_active_runs_per_user:
            return False
        return True

    async def check_connector_execution_budget(self, user_id: uuid.UUID, executions_so_far: int) -> bool:
        if executions_so_far >= self.settings.orchestration_max_executions_per_run:
            return False
        return True
        
    async def acquire_connector_lease(self, connector_name: str, lease_id: str, ttl_seconds: int = 180) -> bool:
        """
        Atomically acquires a concurrency lease for a specific connector.
        Returns True if acquired, False if at limit or Redis unavailable.
        """
        import time
        max_concurrency = getattr(self.settings, f"{connector_name}_max_concurrent_runs", 10)
        
        zset_key = f"connector:concurrency:{connector_name}"
        current_time = int(time.time())
        expiry_time = current_time + ttl_seconds
        
        try:
            result = await self._acquire_script(
                keys=[zset_key],
                args=[lease_id, current_time, expiry_time, max_concurrency]
            )
            return bool(result)
        except Exception as e:
            logger.error("redis_lease_failed", details={"context": "acquire_connector_lease", "connector": connector_name, "error": str(e)})
            return False
            
    async def release_connector_lease(self, connector_name: str, lease_id: str) -> None:
        """Releases an acquired concurrency lease."""
        zset_key = f"connector:concurrency:{connector_name}"
        try:
            await self.redis.zrem(zset_key, lease_id)
        except Exception as e:
            logger.error("redis_release_failed", details={"context": "release_connector_lease", "connector": connector_name, "error": str(e)})
