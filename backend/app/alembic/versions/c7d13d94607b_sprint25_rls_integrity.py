"""sprint25_rls_integrity

Revision ID: c7d13d94607b
Revises: 49a9656ea2e1
Create Date: 2026-07-15 19:53:01.879695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d13d94607b'
down_revision: Union[str, None] = '49a9656ea2e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE identity_orchestration_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE identity_orchestration_runs FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS identity_orchestration_runs_isolation_policy ON identity_orchestration_runs")
    op.execute("""
        CREATE POLICY identity_orchestration_runs_isolation_policy ON identity_orchestration_runs
        USING (user_id = current_setting('rls.user_id', true)::uuid)
    """)
    
    # Assert pg_class and pg_policies programmatic verification
    op.execute("""
        DO $$
        DECLARE
            rls_enabled boolean;
            force_rls boolean;
            policy_exists boolean;
        BEGIN
            SELECT relrowsecurity, relforcerowsecurity 
            INTO rls_enabled, force_rls 
            FROM pg_class 
            WHERE relname = 'identity_orchestration_runs';
            
            IF NOT rls_enabled THEN
                RAISE EXCEPTION 'RLS not enabled on identity_orchestration_runs';
            END IF;
            
            IF NOT force_rls THEN
                RAISE EXCEPTION 'FORCE RLS not enabled on identity_orchestration_runs';
            END IF;
            
            SELECT EXISTS (
                SELECT 1 FROM pg_policies 
                WHERE tablename = 'identity_orchestration_runs' 
                AND policyname = 'identity_orchestration_runs_isolation_policy'
            ) INTO policy_exists;
            
            IF NOT policy_exists THEN
                RAISE EXCEPTION 'Policy identity_orchestration_runs_isolation_policy not found';
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS identity_orchestration_runs_isolation_policy ON identity_orchestration_runs")
