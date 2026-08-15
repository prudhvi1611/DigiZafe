"""sprint7_remediation_engine"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_sprint7_remediation"
down_revision: str | None = "006_sprint6_rec_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_optout_state",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("broker_id", sa.String(64), nullable=False),
        sa.Column("broker_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(48), nullable=False, server_default="pending"),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_runs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "broker_id", name="uq_broker_optout_user_broker"),
    )
    op.create_index("ix_broker_optout_state_user_id", "broker_optout_state", ["user_id"])
    op.create_index("ix_broker_optout_state_broker_id", "broker_optout_state", ["broker_id"])
    op.create_index("ix_broker_optout_state_status", "broker_optout_state", ["status"])

    op.create_table(
        "remediation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recommendation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(64), nullable=False, server_default="broker_optout"),
        sa.Column("status", sa.String(48), nullable=False, server_default="pending"),
        sa.Column("dry_run", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("broker_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("progress_pct", sa.Float(), server_default="0", nullable=False),
        sa.Column("message", sa.String(512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("profile_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_remediation_jobs_user_id", "remediation_jobs", ["user_id"])
    op.create_index("ix_remediation_jobs_status", "remediation_jobs", ["status"])

    op.create_table(
        "remediation_job_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("remediation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("broker_id", sa.String(64), nullable=False),
        sa.Column("broker_name", sa.String(128), nullable=False),
        sa.Column("status", sa.String(48), nullable=False, server_default="pending"),
        sa.Column("skip_reason", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("result_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_remediation_job_items_job_id", "remediation_job_items", ["job_id"])
    op.create_index("ix_remediation_job_items_status", "remediation_job_items", ["status"])

    op.create_table(
        "captcha_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("remediation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("broker_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("page_url", sa.String(1024), nullable=True),
        sa.Column("captcha_type", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("sitekey", sa.String(256), nullable=True),
        sa.Column("solution_token", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("solved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_captcha_queue_user_id", "captcha_queue", ["user_id"])
    op.create_index("ix_captcha_queue_status", "captcha_queue", ["status"])

    op.create_table(
        "freeze_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column("label", sa.String(256), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="todo"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "target_id", name="uq_freeze_user_target"),
    )

    op.create_table(
        "generated_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("regime", sa.String(32), nullable=False, server_default="ccpa"),
        sa.Column("recipient_name", sa.String(256), nullable=True),
        sa.Column("recipient_email", sa.String(320), nullable=True),
        sa.Column("subject", sa.String(512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_generated_requests_user_id", "generated_requests", ["user_id"])
    op.create_index("ix_generated_requests_kind", "generated_requests", ["kind"])

    for table in (
        "broker_optout_state",
        "remediation_jobs",
        "remediation_job_items",
        "captcha_queue",
        "freeze_checklist_items",
        "generated_requests",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_self ON {table}
            FOR ALL
            USING (user_id::text = current_setting('app.current_user_id', true))
            WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
        """)


def downgrade() -> None:
    for table in (
        "generated_requests",
        "freeze_checklist_items",
        "captcha_queue",
        "remediation_job_items",
        "remediation_jobs",
        "broker_optout_state",
    ):
        op.execute(f"DROP POLICY IF EXISTS {table}_self ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
