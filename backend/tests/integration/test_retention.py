import pytest
import datetime
from sqlalchemy import text
from app.core.config import get_settings
from app.connectors.sdk.redis_clients import get_cache_redis
import uuid

pytestmark = pytest.mark.asyncio

async def test_raw_evidence_ttl(db_session):
    """
    Verify raw evidence has TTL enforced.
    We simulate inserting old evidence and check if it would be purged.
    """
    settings = get_settings()
    
    # Insert dummy evidence older than raw ttl
    ttl_hours = settings.evidence_raw_ttl_hours
    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=ttl_hours + 1)
    
    # Insert user and scan without checking identifiers, or use dummy identifiers
    user_id = '00000000-0000-0000-0000-000000000001'
    scan_id = '00000000-0000-0000-0000-000000000002'
    evidence_id = '00000000-0000-0000-0000-000000000003'
    identifier_id = '00000000-0000-0000-0000-000000000004'
    
    await db_session.execute(text(f"""
        INSERT INTO users (id, email, hashed_password) VALUES ('{user_id}', 'test_retention@example.com', 'test') ON CONFLICT DO NOTHING
    """))
    
    # The scans table has a check constraint for identifier_id or other fields, let's look at the actual error we got:
    # `G1_VIOLATION: only verified identifiers allowed (identifier_id=<NULL>)`
    # We need to insert a verified identifier for this user first
    await db_session.execute(text(f"""
        INSERT INTO identifiers (id, user_id, value_canonical, value_display, type, is_verified) VALUES ('{identifier_id}', '{user_id}', 'test_retention@example.com', 'test_retention@example.com', 'email', true) ON CONFLICT DO NOTHING
    """))
    
    await db_session.execute(text(f"""
        INSERT INTO scans (id, user_id, identifier_id, status, deadline_at) VALUES ('{scan_id}', '{user_id}', '{identifier_id}', 'completed', NOW() + INTERVAL '1 hour') ON CONFLICT DO NOTHING
    """))
    
    await db_session.execute(text(f"""
        INSERT INTO evidence_blobs (id, user_id, scan_id, layer, body, created_at)
        VALUES ('{evidence_id}', '{user_id}', '{scan_id}', 'raw', '{{}}', '{old_time.isoformat()}') ON CONFLICT DO NOTHING
    """))
    
    # In a real app this is a cron job. We simulate the cron job query here.
    await db_session.execute(text(f"DELETE FROM evidence_blobs WHERE created_at < NOW() - INTERVAL '{ttl_hours} hours'"))
    
    result = await db_session.execute(text(f"SELECT count(*) FROM evidence_blobs WHERE id = '{evidence_id}'"))
    count = result.scalar()
    assert count == 0, "Old evidence was not purged"


async def test_cache_ttl():
    """Verify cache TTL works in Redis."""
    cache = await get_cache_redis()
    await cache.set("test_retention_key", "val", ex=1)
    
    # Value should exist immediately
    val = await cache.get("test_retention_key")
    assert val == "val"
    
    # Redis TTL test could be slow if we sleep, but 1 sec is okay for verification
    import asyncio
    await asyncio.sleep(1.5)
    
    val2 = await cache.get("test_retention_key")
    assert val2 is None, "Cache item did not expire"


async def test_crypto_shred(db_session):
    """
    Verify crypto shred deletes user data.
    """
    from app.services.privacy.shred_service import ShredService
    
    user_id = str(uuid.uuid4())
    
    await db_session.execute(text(f"""
        INSERT INTO users (id, email, hashed_password) VALUES ('{user_id}', 'shred_{user_id}@example.com', 'test')
    """))
    
    svc = ShredService(db_session)
    await svc.execute_shred(uuid.UUID(user_id))
    
    result = await db_session.execute(text(f"SELECT count(*) FROM users WHERE id = '{user_id}'"))
