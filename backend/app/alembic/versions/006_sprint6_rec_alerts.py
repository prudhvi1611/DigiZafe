"""sprint6_recommendations_alerts"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_sprint6_rec_alerts"
down_revision: str | None = "005_sprint5_identity_pdss"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("score_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("freeze_recommended", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("dag_order", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_recommendation_plans_user_id", "recommendation_plans", ["user_id"])
    op.create_index("ix_recommendation_plans_created_at", "recommendation_plans", ["created_at"])

    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("lane", sa.String(32), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("urgency", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("effort_hours", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("roi", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("priority", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("depends_on", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("related_finding_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("links", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("playbook_key", sa.String(128), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("model_version", sa.String(64), nullable=False, server_default="rec-v1.0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])
    op.create_index("ix_recommendations_plan_id", "recommendations", ["plan_id"])
    op.create_index("ix_recommendations_code", "recommendations", ["code"])
    op.create_index("ix_recommendations_lane", "recommendations", ["lane"])
    op.create_index("ix_recommendations_status", "recommendations", ["status"])
    op.create_index("ix_recommendations_priority", "recommendations", ["priority"])

    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False, server_default="info"),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("dismissed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])
    op.create_index("ix_alerts_kind", "alerts", ["kind"])
    op.create_index("ix_alerts_read", "alerts", ["read"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])

    op.create_table(
        "rescan_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("interval_hours", sa.Integer(), server_default="168", nullable=False),
        sa.Column("last_rescan_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_eligible_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_rescan_policies_user_id", "rescan_policies", ["user_id"])
    op.create_index("ix_rescan_policies_identifier_id", "rescan_policies", ["identifier_id"])

    for table in ("recommendation_plans", "recommendations", "alerts", "rescan_policies"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    for pol, tbl in [
        ("recommendation_plans_self", "recommendation_plans"),
        ("recommendations_self", "recommendations"),
        ("alerts_self", "alerts"),
        ("rescan_policies_self", "rescan_policies"),
    ]:
        op.execute(f"""
            CREATE POLICY {pol} ON {tbl}
            FOR ALL
            USING (user_id::text = current_setting('app.current_user_id', true))
            WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
        """)


def downgrade() -> None:
    for pol, tbl in [
        ("rescan_policies_self", "rescan_policies"),
        ("alerts_self", "alerts"),
        ("recommendations_self", "recommendations"),
        ("recommendation_plans_self", "recommendation_plans"),
    ]:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {tbl}")
    for table in ("rescan_policies", "alerts", "recommendations", "recommendation_plans"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
