"""sprint8_privacy_rights_explain"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_sprint8_privacy"
down_revision: str | None = "007_sprint7_remediation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_export_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("include_audit", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("include_egress", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("package", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_data_export_jobs_user_id", "data_export_jobs", ["user_id"])
    op.create_index("ix_data_export_jobs_status", "data_export_jobs", ["status"])

    op.create_table(
        "account_deletion_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("confirm_phrase_ok", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_account_deletion_requests_user_id", "account_deletion_requests", ["user_id"])
    op.create_index("ix_account_deletion_requests_status", "account_deletion_requests", ["status"])

    op.create_table(
        "narrative_briefings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score_snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("score_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mode", sa.String(32), nullable=False, server_default="deterministic"),
        sa.Column("model_name", sa.String(128), nullable=True),
        sa.Column("title", sa.String(256), nullable=False, server_default="Exposure briefing"),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("facts_used", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("grounded", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_narrative_briefings_user_id", "narrative_briefings", ["user_id"])
    op.create_index("ix_narrative_briefings_created_at", "narrative_briefings", ["created_at"])

    for table in ("data_export_jobs", "account_deletion_requests", "narrative_briefings"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_self ON {table}
            FOR ALL
            USING (user_id::text = current_setting('app.current_user_id', true))
            WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
        """)


def downgrade() -> None:
    for table in ("narrative_briefings", "account_deletion_requests", "data_export_jobs"):
        op.execute(f"DROP POLICY IF EXISTS {table}_self ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
