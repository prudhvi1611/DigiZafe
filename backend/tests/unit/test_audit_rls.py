import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.models.user import User
from app.models.orchestration import ConnectorExecutionPlanItem

@pytest.mark.asyncio
async def test_audit_rls_isolation(db_session: AsyncSession):
    # Two users
    u1 = User(email=f"u1_{uuid.uuid4()}@ex.com", hashed_password="pw")
    u2 = User(email=f"u2_{uuid.uuid4()}@ex.com", hashed_password="pw")
    db_session.add_all([u1, u2])
    await db_session.commit()
    
    from app.models.orchestration import IdentityOrchestrationRun
    run1 = IdentityOrchestrationRun(user_id=u1.id, input_fingerprint="test-fp-1")
    run2 = IdentityOrchestrationRun(user_id=u2.id, input_fingerprint="test-fp-2")
    db_session.add_all([run1, run2])
    await db_session.commit()
    
    plan1 = ConnectorExecutionPlanItem(
        orchestration_run_id=run1.id,
        connector_type="maigret",
        capability="discovery",
        decision="execute",
        execution_status="pending",
        execution_mode="live"
    )
    db_session.add(plan1)
    
    plan2 = ConnectorExecutionPlanItem(
        orchestration_run_id=run2.id,
        connector_type="osintgram",
        capability="discovery",
        decision="execute",
        execution_status="pending",
        execution_mode="live"
    )
    db_session.add(plan2)
    await db_session.commit()
    db_session.expunge_all()
    
    # Create non-superuser role to actually test RLS (superusers bypass it)
    await db_session.execute(text("DROP ROLE IF EXISTS rls_test_user"))
    await db_session.execute(text("CREATE ROLE rls_test_user"))
    await db_session.execute(text("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rls_test_user"))
    await db_session.commit()

    # RLS query as u1
    await db_session.execute(text("SET LOCAL ROLE rls_test_user"))
    await db_session.execute(text("SELECT set_config('rls.user_id', :u_id, true)"), {"u_id": str(u1.id)})
    res1 = (await db_session.execute(select(IdentityOrchestrationRun))).scalars().all()
    assert len(res1) == 1

    # RLS query as u2
    await db_session.execute(text("SET LOCAL ROLE rls_test_user"))
    await db_session.execute(text("SELECT set_config('rls.user_id', :u_id, true)"), {"u_id": str(u2.id)})
    res2 = (await db_session.execute(select(IdentityOrchestrationRun))).scalars().all()
    assert len(res2) == 1
    
    # Verify isolation
    assert res1[0].id == run1.id
    assert res2[0].id == run2.id
    
    await db_session.execute(text("RESET ROLE"))
