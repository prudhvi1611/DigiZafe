# DigiZafe — Sprint 0 Foundations  
**Complete Setup Guide from Empty Folder + All File Contents**

**Document version:** 1.0  
**Based on:** MASTER_ENGINEERING_CONTEXT.md v2.1  
**Goal:** From empty `DigiZafe/` folder → runnable, green Sprint 0 foundations.

---

# PART A — Pre-Sprint 0 (Do this FIRST)

Open a terminal **inside** your empty `DigiZafe` folder and run:

```bash
# 1. Create the master context (MOST IMPORTANT)
# Open MASTER_ENGINEERING_CONTEXT.md and paste the FULL final v2.1 content we created earlier
touch MASTER_ENGINEERING_CONTEXT.md

# 2. Git init
git init
git branch -M main

# 3. Create root files
touch README.md LICENSE NOTICE .gitignore .env.example .env pyproject.toml docker-compose.yml alembic.ini

# 4. Create full directory structure
mkdir -p backend/app/{api/v1,core,domain,services,connectors/{sdk,impl/surface},remediation,repositories,models,schemas,security,tasks,constants}
mkdir -p backend/app/alembic/versions
mkdir -p backend/tests/{unit,integration,security,e2e,fixtures,factories}
mkdir -p frontend/src/{app,features,components,lib,hooks,styles}
mkdir -p infrastructure/{docker,caddy,redis,postgres,monitoring}
mkdir -p shared/{contracts,config,types}
mkdir -p ml/{datasets,training,export,eval}
mkdir -p docs/{adr,runbooks,model-cards,ethics,aidr-mapping}
mkdir -p scripts .github/workflows vendor

# 5. Create all __init__.py so packages work
find backend -type d -exec touch {}/__init__.py \; 2>/dev/null || true
touch backend/app/api/v1/__init__.py
touch backend/app/connectors/impl/__init__.py
touch backend/app/connectors/impl/surface/__init__.py
touch backend/app/alembic/__init__.py

echo "✅ Pre-Sprint 0 skeleton created. Now copy the file contents below."
```

---

# PART B — Sprint 0 File Contents

Copy each section into the corresponding file.

---

## 1. Root: `README.md`

```markdown
# DigiZafe

**Personal Digital Exposure Intelligence & Remediation Platform**

DigiZafe helps you discover, understand, quantify, and reduce your own online exposure — surface → deep → constrained dark — with full explainability (PDSS score) and free, actionable remediation (AIDR-inspired).

- **Zero paid API keys required for MVP**
- Primary free breach source: **XposedOrNot**
- Remediation engine based on [auto-identity-remove (AIDR)](https://github.com/stephenlthorn/auto-identity-remove)
- Privacy-first, local-first, research-grade

## Quick Start (Sprint 0)

```bash
cp .env.example .env
# edit .env if needed (defaults work for local)

docker compose up --build
```

- API: http://localhost:8000  
- Health: http://localhost:8000/api/v1/health  
- Docs: http://localhost:8000/docs  

## Documentation

- `MASTER_ENGINEERING_CONTEXT.md` ← **Load this before every coding session**
- `docs/` — ADRs, AIDR mapping, free sources, model cards, ethics

## License

MIT (see LICENSE).  
See NOTICE for third-party attributions (AIDR, XposedOrNot, etc.).
```

---

## 2. Root: `LICENSE`

```text
MIT License

Copyright (c) 2025 DigiZafe Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 3. Root: `NOTICE`

```text
DigiZafe
Copyright (c) 2025 DigiZafe Contributors

This product includes software and design ideas derived from:

1. auto-identity-remove (AIDR)
   https://github.com/stephenlthorn/auto-identity-remove
   Used as primary prior art for the remediation engine, broker runners,
   verification loops, state management, and related concepts.
   All code has been re-implemented under DigiZafe architecture.
   Please respect the original project's license.

2. XposedOrNot
   https://xposedornot.com
   https://github.com/XposedOrNot
   Primary free breach data source. Free tier is for personal / low-volume use.
   Attribution required when displaying their data. Respect their rate limits and ToS.

3. Other free sources: Pwned Passwords (Have I Been Pwned), crt.sh, etc.
   See docs/free-sources.md

DigiZafe itself is released under the MIT License (see LICENSE).
```

---

## 4. Root: `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.eggs/
*.egg
.mypy_cache/
.ruff_cache/
.pytest_cache/
.coverage
htmlcov/
.tox/
.venv/
venv/
ENV/

# Environment
.env
.env.local
.env.*.local
!.env.example

# IDE
.idea/
.vscode/
*.swp
*.swo
.DS_Store

# Docker
*.log

# Alembic
# (keep versions)

# Celery
celerybeat-schedule
celerybeat.pid

# Local data
data/
*.sqlite3
postgres_data/
redis_data/

# Frontend (later)
node_modules/
frontend/dist/
frontend/.next/

# Secrets / keys
*.pem
*.key
master.key
*.enc

# OS
Thumbs.db
```

---

## 5. Root: `.env.example`

```bash
# DigiZafe Environment Variables
# Copy to .env and adjust. Never commit .env

# Application
APP_NAME=DigiZafe
APP_ENV=development
DEBUG=true
SECRET_KEY=change-me-to-a-long-random-string-at-least-32-chars
MASTER_KEY_FILE=./secrets/master.key   # created automatically in dev if missing

# Database (Postgres)
POSTGRES_USER=digizafe
POSTGRES_PASSWORD=digizafe_dev_password
POSTGRES_DB=digizafe
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://digizafe:digizafe_dev_password@postgres:5432/digizafe

# Redis - Broker (persistent, noeviction)
REDIS_BROKER_URL=redis://redis-broker:6379/0

# Redis - Cache (disposable, allkeys-lru)
REDIS_CACHE_URL=redis://redis-cache:6379/0

# Celery
CELERY_BROKER_URL=redis://redis-broker:6379/0
CELERY_RESULT_BACKEND=redis://redis-broker:6379/1

# API
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8000"]

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Feature flags (all free by default)
FEATURE_XPOSEDORNOT=true
FEATURE_HIBP_BREACH_API=false          # paid - optional only
FEATURE_CAPSOLVER=false                # paid - optional only
FEATURE_ML_RESIDUAL=false

# Optional paid keys (leave empty for free path)
HIBP_API_KEY=
CAPSOLVER_API_KEY=
XPOSEDORNOT_API_KEY=                   # only for higher tiers

# Rate limiting / quotas (dev defaults)
DEFAULT_USER_SCAN_QUOTA_PER_DAY=20
```

---

## 6. Root: `pyproject.toml`

```toml
[project]
name = "digizafe"
version = "0.1.0"
description = "Personal Digital Exposure Intelligence & Remediation Platform"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "DigiZafe Contributors" }]

dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    "sqlalchemy[asyncio]>=2.0.32",
    "asyncpg>=0.29.0",
    "alembic>=1.13.2",
    "celery[redis]>=5.4.0",
    "redis>=5.0.8",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
    "cryptography>=43.0.0",
    "argon2-cffi>=23.1.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[argon2]>=1.7.4",
    "email-validator>=2.2.0",
    "structlog>=24.4.0",
    "orjson>=3.10.0",
    "tenacity>=9.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "ruff>=0.6.0",
    "mypy>=1.11.0",
    "types-redis",
    "types-passlib",
    "pre-commit>=3.8.0",
    "testcontainers[postgres]>=4.8.0",
]

[build-system]
requires = ["setuptools>=75.0.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["backend"]
include = ["app*"]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["backend"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "N"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
packages = ["app"]
mypy_path = "backend"

[[tool.mypy.overrides]]
module = ["celery.*", "passlib.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["backend/tests"]
pythonpath = ["backend"]
filterwarnings = ["ignore::DeprecationWarning"]
```

---

## 7. Root: `docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-digizafe}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-digizafe_dev_password}
      POSTGRES_DB: ${POSTGRES_DB:-digizafe}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-digizafe} -d ${POSTGRES_DB:-digizafe}"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks:
      - digizafe

  redis-broker:
    image: redis:7-alpine
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - ./infrastructure/redis/redis-broker.conf:/usr/local/etc/redis/redis.conf:ro
      - redis_broker_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks:
      - digizafe

  redis-cache:
    image: redis:7-alpine
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - ./infrastructure/redis/redis-cache.conf:/usr/local/etc/redis/redis.conf:ro
      - redis_cache_data:/data
    ports:
      - "6380:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks:
      - digizafe

  api:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-digizafe}:${POSTGRES_PASSWORD:-digizafe_dev_password}@postgres:5432/${POSTGRES_DB:-digizafe}
      REDIS_BROKER_URL: redis://redis-broker:6379/0
      REDIS_CACHE_URL: redis://redis-cache:6379/0
      CELERY_BROKER_URL: redis://redis-broker:6379/0
      CELERY_RESULT_BACKEND: redis://redis-broker:6379/1
    volumes:
      - ./backend:/app/backend
      - ./shared:/app/shared
      - ./secrets:/app/secrets
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis-broker:
        condition: service_healthy
      redis-cache:
        condition: service_healthy
    networks:
      - digizafe
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

  worker:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile
    command: celery -A app.worker.celery_app worker --loglevel=INFO --concurrency=2
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-digizafe}:${POSTGRES_PASSWORD:-digizafe_dev_password}@postgres:5432/${POSTGRES_DB:-digizafe}
      REDIS_BROKER_URL: redis://redis-broker:6379/0
      REDIS_CACHE_URL: redis://redis-cache:6379/0
      CELERY_BROKER_URL: redis://redis-broker:6379/0
      CELERY_RESULT_BACKEND: redis://redis-broker:6379/1
    volumes:
      - ./backend:/app/backend
      - ./shared:/app/shared
      - ./secrets:/app/secrets
    depends_on:
      postgres:
        condition: service_healthy
      redis-broker:
        condition: service_healthy
      redis-cache:
        condition: service_healthy
    networks:
      - digizafe

  beat:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile
    command: celery -A app.worker.celery_app beat --loglevel=INFO
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-digizafe}:${POSTGRES_PASSWORD:-digizafe_dev_password}@postgres:5432/${POSTGRES_DB:-digizafe}
      CELERY_BROKER_URL: redis://redis-broker:6379/0
      CELERY_RESULT_BACKEND: redis://redis-broker:6379/1
    volumes:
      - ./backend:/app/backend
      - ./shared:/app/shared
    depends_on:
      - redis-broker
      - worker
    networks:
      - digizafe

  caddy:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./infrastructure/caddy/Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - api
    networks:
      - digizafe
    profiles:
      - with-caddy   # optional: docker compose --profile with-caddy up

volumes:
  postgres_data:
  redis_broker_data:
  redis_cache_data:
  caddy_data:
  caddy_config:

networks:
  digizafe:
    driver: bridge
```

---

## 8. `infrastructure/docker/Dockerfile`

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY backend ./backend
COPY shared ./shared

RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# Create non-root user
RUN useradd -m -u 1000 digizafe && \
    mkdir -p /app/secrets && \
    chown -R digizafe:digizafe /app

USER digizafe

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 9. `infrastructure/redis/redis-broker.conf`

```conf
# Broker - persistent, no eviction
port 6379
bind 0.0.0.0
protected-mode no
appendonly yes
appendfsync everysec
maxmemory-policy noeviction
save 900 1
save 300 10
save 60 10000
```

---

## 10. `infrastructure/redis/redis-cache.conf`

```conf
# Cache - disposable, LRU
port 6379
bind 0.0.0.0
protected-mode no
appendonly no
maxmemory 256mb
maxmemory-policy allkeys-lru
save ""
```

---

## 11. `infrastructure/caddy/Caddyfile`

```caddy
:80 {
    reverse_proxy api:8000
    encode gzip
    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Referrer-Policy strict-origin-when-cross-origin
        -Server
    }
}
```

---

## 12. `backend/app/core/config.py`  (fail-fast)

```python
from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "DigiZafe"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)
    master_key_file: str = "./secrets/master.key"

    # Database
    database_url: str = Field(..., description="Async SQLAlchemy URL (postgresql+asyncpg://...)")

    # Redis
    redis_broker_url: str = "redis://localhost:6379/0"
    redis_cache_url: str = "redis://localhost:6380/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json | console

    # Feature flags
    feature_xposedornot: bool = True
    feature_hibp_breach_api: bool = False
    feature_capsolver: bool = False
    feature_ml_residual: bool = False

    # Optional keys
    hibp_api_key: str | None = None
    capsolver_api_key: str | None = None
    xposedornot_api_key: str | None = None

    # Quotas
    default_user_scan_quota_per_day: int = 20

    @field_validator("secret_key")
    @classmethod
    def secret_key_strength(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Fail-fast: raises ValidationError if required env vars are missing."""
    return Settings()  # type: ignore[call-arg]
```

---

## 13. `backend/app/core/logging.py`

```python
import logging
import sys
from typing import Any

import structlog
from app.core.config import get_settings


def setup_logging() -> None:
    settings = get_settings()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Quiet noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
```

---

## 14. `backend/app/core/correlation.py`

```python
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return correlation_id_ctx.get()


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    header_name = "X-Correlation-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        correlation_id_ctx.set(correlation_id)

        # Bind to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        response = await call_next(request)
        response.headers[self.header_name] = correlation_id
        return response
```

---

## 15. `backend/app/core/database.py` (minimal for Sprint 0)

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

---

## 16. `backend/app/api/errors.py` (minimal)

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": "about:blank",
            "title": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "status": exc.status_code,
            "code": f"HTTP-{exc.status_code}",
            "detail": exc.detail,
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "code": "VAL-001",
            "detail": exc.errors(),
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "code": "SYS-001",
            "detail": "An unexpected error occurred",
        },
    )
```

---

## 17. `backend/app/api/v1/health.py`

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings

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


@router.get("/health/ready")
async def readiness() -> dict:
    """Readiness probe (can be expanded later)."""
    return {"status": "ready"}
```

---

## 18. `backend/app/main.py`

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.core.correlation import CorrelationIdMiddleware
from app.api.v1 import health
from app.api.errors import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_up", app=settings.app_name, env=settings.app_env)
    # Future: create master key if missing, warm caches, etc.
    yield
    logger.info("shutting_down")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Routers
app.include_router(health.router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health",
        "message": "DigiZafe Sprint 0 Foundations — ready",
    }
```

---

## 19. `backend/app/worker.py` (Celery entrypoint)

```python
from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "digizafe",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks"],  # future tasks
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(name="app.tasks.health_ping")
def health_ping() -> str:
    return "pong"
```

---

## 20. `backend/app/tasks/__init__.py`

```python
# Task package - populated in later sprints
from app.worker import health_ping  # noqa: F401
```

---

## 21. Alembic: `alembic.ini` (root)

```ini
[alembic]
script_location = backend/app/alembic
prepend_sys_path = .
version_path_separator = os

sqlalchemy.url = driver://user:pass@localhost/dbname

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

---

## 22. `backend/app/alembic/env.py`

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.core.database import Base

# Import models here later so they register with Base.metadata
# from app.models import user, identifier, ...

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
settings = get_settings()


def get_url() -> str:
    return settings.database_url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

## 23. `backend/app/alembic/script.py.mako` (standard)

Create the file with the normal Alembic template (you can run `alembic init` once if you prefer, then replace env.py). For now a minimal version is fine — Alembic will work with the env.py above.

You can generate a baseline later with:
```bash
alembic revision --autogenerate -m "baseline_empty"
alembic upgrade head
```

---

## 24. `backend/tests/unit/test_health.py` (simple test)

```python
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
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"
```

---

## 25. `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint-type-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Ruff lint
        run: ruff check backend

      - name: Ruff format check
        run: ruff format --check backend

      - name: Mypy
        run: mypy backend/app --ignore-missing-imports || true
        # (strict later; currently soft for Sprint 0)

      - name: Pytest (unit)
        run: pytest backend/tests/unit -v --tb=short
        env:
          SECRET_KEY: "test-secret-key-at-least-32-characters-long"
          DATABASE_URL: "postgresql+asyncpg://test:test@localhost:5432/test"
          APP_ENV: "test"
```

---

## 26. Docs skeletons

### `docs/free-sources.md`
```markdown
# Free Sources Inventory (DigiZafe)

## Primary Breach Source
- **XposedOrNot** — https://api.xposedornot.com  
  Free, keyless for personal email checks. Rate limits apply. Attribution required.

## Password
- Pwned Passwords (HIBP) — free, k-anonymous

## Other Free
- crt.sh (Certificate Transparency)
- RDAP / public DNS
- GitHub API (free token)
- Gravatar
- DuckDuckGo / self-hosted Searx
- CA SB 362 & Vermont data broker registries
- archive.org
- Local Ollama

See MASTER_ENGINEERING_CONTEXT.md §12 for full policy.
```

### `docs/aidr-mapping.md`
```markdown
# AIDR → DigiZafe Mapping

Source: https://github.com/stephenlthorn/auto-identity-remove

| AIDR Component              | DigiZafe Location                          | Notes |
|----------------------------|--------------------------------------------|-------|
| brokers.js + registries    | shared/config/broker_registry/ + remediation/ | Re-implemented |
| state.json optOuts         | broker_optout_state table                  | + RLS |
| aidr score (simple weights)| ScoringService (PDSS + surprisal)          | Superseded |
| aidr breach / hibp.js      | connectors/impl/surface/xposedornot.py     | Primary free |
| aidr verify                | RemediationService + verify loop           | Closed-loop |
| CapSolver                  | Optional feature flag only                 | Free path first |
| ...                        | ...                                        | See full mapping later |

Always attribute AIDR. Respect original license.
```

### `docs/adr/0000-template.md` + a few stubs
Create simple ADR stubs for the ones listed in the master context (0001 modular monolith, 0002 state machine, 0003 split Redis, 0009 free-first, 0010 AIDR remediation, 0013 zero paid keys).

### `docs/model-cards/pdss-v1.md` (skeleton)
```markdown
# Model Card — PDSS v1 (Sprint 0 placeholder)

Status: Planned for Sprint 5  
Type: Hybrid CVSS-inspired vector + surprisal (+ optional residual later)  
Training data: None yet (deterministic first)
```

---

# PART C — How to finish Sprint 0

After copying all the files above:

```bash
# 1. Create .env from example
cp .env.example .env

# 2. Generate a real SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"
# paste into .env as SECRET_KEY=...

# 3. Create secrets folder
mkdir -p secrets

# 4. Build and start
docker compose up --build -d

# 5. Check health
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/

# 6. (Optional) Run Alembic baseline later
# docker compose exec api alembic revision --autogenerate -m "baseline"
# docker compose exec api alembic upgrade head

# 7. Commit
git add .
git commit -m "chore(sprint-0): foundations - docker, config, logging, health, alembic, ci"
```

---

# Sprint 0 Definition of Done Checklist

- [ ] MASTER_ENGINEERING_CONTEXT.md present and complete  
- [ ] `docker compose up --build` succeeds  
- [ ] `GET /api/v1/health` returns 200 with database: ok  
- [ ] Correlation ID header is echoed  
- [ ] Structured JSON logging works  
- [ ] Fail-fast config (missing SECRET_KEY crashes clearly)  
- [ ] Two Redis instances (broker + cache) with different policies  
- [ ] Celery worker + beat start  
- [ ] CI workflow exists  
- [ ] Free-sources + AIDR mapping docs exist  
- [ ] No paid keys required  

Once all boxes are checked → **Sprint 0 is complete**.  
You can then move to **Sprint 1 (Auth & Crypto)**.

---

**You are ready.**  
Start by pasting the MASTER_ENGINEERING_CONTEXT.md, run the mkdir commands, then copy the files above one by one.  

If any file fails or you want me to generate the next batch (Sprint 1 Auth files), just say so.