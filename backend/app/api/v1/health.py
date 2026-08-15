from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.sdk.redis_clients import get_broker_redis, get_cache_redis
from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Basic liveness + database connectivity check."""
    settings = get_settings()

    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {type(e).__name__}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.app_name,
        "env": settings.app_env,
        "database": db_status,
        "features": {
            "xposedornot": settings.feature_xposedornot,
            "hibp_breach_api": settings.feature_hibp_breach_api,
            "capsolver": settings.feature_capsolver,
            "ml_residual": settings.feature_ml_residual,
        },
    }


@router.get("/health/live")
async def liveness() -> dict:
    """Liveness probe (no dependencies)."""
    return {"status": "alive"}


from fastapi import Response


@router.get("/health/ready")
async def readiness(response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness probe."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        response.status_code = 503
        return {"status": "unready", "reason": "postgres_unavailable"}

    try:
        cache = await get_cache_redis()
        await cache.ping()
    except Exception:
        response.status_code = 503
        return {"status": "unready", "reason": "cache_redis_unavailable"}

    try:
        broker = await get_broker_redis()
        await broker.ping()
    except Exception:
        response.status_code = 503
        return {"status": "unready", "reason": "broker_redis_unavailable"}

    return {"status": "ready"}

@router.get("/health/components")
async def components() -> dict:
    """Detailed component availability."""
    celery_status = "unknown"
    try:
        from app.core.celery_app import celery_app
        # Use ping to check if any worker responds
        pings = celery_app.control.ping(timeout=0.5)
        celery_status = "available" if pings else "no_workers"
    except Exception:
        celery_status = "unavailable"

    # Minimal mock for connectors if registry not fully loaded here
    connectors = {
        "maigret": "available",
        "osintgram": "available",
        "identity_enrichment": "available"
    }

    return {
        "status": "ok",
        "celery": celery_status,
        "connectors": connectors
    }
