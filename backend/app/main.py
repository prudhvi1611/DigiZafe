from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from app.api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.api.v1 import (
    alerts,
    auth,
    connectors,
    health,
    identifiers,
    identity,
    identity_assessment,
    identity_discovery,
    osintgram,
    privacy,
    recommendations,
    remediation,
    scans,
    scores,
    temporal,
)
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.metrics import MetricsMiddleware, metrics_response
from app.core.startup_validation import validate_production_config
from app.security.keys import get_key_service
from app.services.catalog_loader import (
    get_linkage_weights,
    get_pdss_catalog,
    get_recommendation_catalog,
)

setup_logging()
logger = structlog.get_logger(__name__)
validate_production_config()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_up", app=settings.app_name, env=settings.app_env)
    
    # Ensure catalogs are loaded on startup
    get_pdss_catalog()
    get_linkage_weights()
    get_recommendation_catalog()
    logger.info("catalogs_loaded")

    # Ensure master key exists (dev auto-create)
    get_key_service()
    
    yield
    logger.info("shutting_down")

app = FastAPI(
    title=settings.app_name,
    version="0.8.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Exception handlers
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# CORS
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(MetricsMiddleware)

# Routers
app.include_router(health.router, prefix=settings.api_v1_prefix)
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(identifiers.router, prefix=settings.api_v1_prefix)
app.include_router(connectors.router, prefix=settings.api_v1_prefix)
app.include_router(scans.router, prefix=settings.api_v1_prefix)
app.include_router(identity.router, prefix=settings.api_v1_prefix)
app.include_router(identity_assessment.router, prefix=settings.api_v1_prefix)
app.include_router(identity_discovery.router, prefix=settings.api_v1_prefix)
app.include_router(osintgram.router, prefix=f"{settings.api_v1_prefix}/discovery/osintgram", tags=["osintgram"])
app.include_router(scores.router, prefix=settings.api_v1_prefix)
app.include_router(recommendations.router, prefix=settings.api_v1_prefix)
app.include_router(alerts.router, prefix=settings.api_v1_prefix)
app.include_router(remediation.router, prefix=settings.api_v1_prefix)
app.include_router(privacy.router, prefix=settings.api_v1_prefix)
app.include_router(temporal.router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "env": settings.app_env,
        "health": f"{settings.api_v1_prefix}/health",
        "message": "DigiZafe Sprint 8 Privacy, Rights, Explain backend — ready",
    }

@app.get("/metrics")
async def metrics():
    return metrics_response()
