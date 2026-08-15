import asyncio
import os
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from app.core.config import get_settings
from alembic.config import Config
from alembic import command

# Use a test database
TEST_DB_NAME = "digizafe_test"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    settings = get_settings()
    # Connect to the default db to create test db
    default_url = settings.database_url
    
    engine = create_async_engine(default_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        # Drop if exists
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE)"))
        # Create test db
        await conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    await engine.dispose()
    
    # Run migrations
    test_db_url = settings.database_url.rsplit('/', 1)[0] + f"/{TEST_DB_NAME}"
    os.environ["DATABASE_URL"] = test_db_url
    
    # Run alembic upgrade head synchronously in a subprocess to avoid event loop conflicts
    import subprocess
    import sys
    env = os.environ.copy()
    env["SECRET_KEY"] = settings.secret_key
    env["PYTHONPATH"] = os.path.abspath("backend")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=os.path.abspath("backend"), env=env, check=True)
    
    yield
    
    # Cleanup
    engine = create_async_engine(default_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME} WITH (FORCE)"))
    await engine.dispose()

@pytest.fixture
async def db_session() -> AsyncSession:
    settings = get_settings()
    test_db_url = settings.database_url.rsplit('/', 1)[0] + f"/{TEST_DB_NAME}"
    
    engine = create_async_engine(test_db_url, pool_pre_ping=True)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()
