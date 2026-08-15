import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.core.database import Base
from app.models.alert import Alert, RescanPolicy  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.connector_config import ConnectorConfig  # noqa: F401
from app.models.consent_egress import ConsentRecord, EgressLedger  # noqa: F401
from app.models.identifier import Identifier, VerificationChallenge  # noqa: F401
from app.models.identity import IdentityCollision, IdentityEdge  # noqa: F401
from app.models.observation_finding import Finding, Observation  # noqa: F401
from app.models.privacy import (  # noqa: F401
    AccountDeletionRequest,
    DataExportJob,
    NarrativeBriefing,
)
from app.models.recommendation import Recommendation, RecommendationPlan  # noqa: F401
from app.models.scan import Scan, ScanConnectorRun  # noqa: F401
from app.models.score import ExplanationRecord, ScoreSnapshot  # noqa: F401
from app.models.user import RefreshToken, User  # noqa: F401

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
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


async def run_migrations_online() -> None:
    # Use config from env, override with settings URL
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.database_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
