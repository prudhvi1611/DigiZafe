import time
from enum import Enum
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"       # Healthy, execution allowed
    OPEN = "open"           # Unhealthy, execution blocked
    HALF_OPEN = "half_open" # Probing recovery


class ConnectorHealthService:
    """Service to track operational connector health and enforce circuit breaking."""

    def __init__(self, redis: Redis):
        self.redis = redis
        self.settings = get_settings()

    async def get_state(self, connector_type: str) -> CircuitBreakerState:
        """
        Determine current circuit breaker state.
        Fails closed (OPEN) if Redis is completely unavailable, to prevent uncontrolled execution on degraded infrastructure.
        """
        try:
            failures_key = f"connector_health:{connector_type}:failures"
            cooldown_key = f"connector_health:{connector_type}:cooldown"
            
            # Check if cooldown is active
            in_cooldown = await self.redis.exists(cooldown_key)
            if in_cooldown:
                return CircuitBreakerState.OPEN
                
            # If cooldown is expired but there are still failures recorded past the threshold,
            # we are in half-open state.
            failures = await self.redis.get(failures_key)
            if failures and int(failures) >= self.settings.circuit_breaker_failure_threshold:
                return CircuitBreakerState.HALF_OPEN
                
            return CircuitBreakerState.CLOSED
        except Exception as e:
            logger.error("redis_unavailable", details={"context": "circuit_breaker_get_state", "error": str(e)})
            return CircuitBreakerState.OPEN

    async def record_success(self, connector_type: str) -> None:
        """
        Records a successful execution, closing the circuit if it was half-open.
        """
        try:
            failures_key = f"connector_health:{connector_type}:failures"
            await self.redis.delete(failures_key)
        except Exception as e:
            logger.error("redis_unavailable", details={"context": "circuit_breaker_record_success", "error": str(e)})

    async def record_failure(self, connector_type: str) -> None:
        """
        Records an operational failure. If threshold is reached, opens the circuit.
        """
        try:
            failures_key = f"connector_health:{connector_type}:failures"
            cooldown_key = f"connector_health:{connector_type}:cooldown"
            
            state = await self.get_state(connector_type)
            
            if state == CircuitBreakerState.HALF_OPEN:
                # Failed a probe, immediately re-open circuit
                await self.redis.set(cooldown_key, "1", ex=self.settings.circuit_breaker_open_cooldown_seconds)
            else:
                # Normal closed state, increment failure counter
                pipe = self.redis.pipeline()
                pipe.incr(failures_key)
                pipe.expire(failures_key, self.settings.circuit_breaker_evaluation_window_seconds, nx=True)
                results = await pipe.execute()
                
                count = results[0]
                if count >= self.settings.circuit_breaker_failure_threshold:
                    # Open circuit
                    await self.redis.set(cooldown_key, "1", ex=self.settings.circuit_breaker_open_cooldown_seconds)
        except Exception as e:
            logger.error("redis_unavailable", details={"context": "circuit_breaker_record_failure", "error": str(e)})
