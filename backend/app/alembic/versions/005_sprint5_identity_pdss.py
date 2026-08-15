"""sprint5_identity_pdss

Revision ID: 005_sprint5_identity_pdss
Revises: 004_sprint4_discovery
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_sprint5_identity_pdss"
down_revision: str | None = "004_sprint4_discovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identity_edges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("left_identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("right_identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("match_weight", sa.Float(), nullable=False),
        sa.Column("match_prob", sa.Float(), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False, server_default="linkage-v1.0.0"),
        sa.Column("review_status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "left_identifier_id", "right_identifier_id", name="uq_identity_edge_pair"),
    )
    op.create_index("ix_identity_edges_user_id", "identity_edges", ["user_id"])
    op.create_index("ix_identity_edges_decision", "identity_edges", ["decision"])
    op.create_index("ix_identity_edges_review_status", "identity_edges", ["review_status"])

    op.create_table(
        "identity_collisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("edge_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identity_edges.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(128), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_identity_collisions_user_id", "identity_collisions", ["user_id"])

    op.create_table(
        "score_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("score_confirmed", sa.Float(), nullable=False),
        sa.Column("score_possible", sa.Float(), nullable=False),
        sa.Column("score_combined", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("vector", sa.String(512), nullable=False),
        sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("contributions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("counterfactuals", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attributions", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("finding_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("trigger", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_score_snapshots_user_id", "score_snapshots", ["user_id"])
    op.create_index("ix_score_snapshots_identifier_id", "score_snapshots", ["identifier_id"])
    op.create_index("ix_score_snapshots_score_combined", "score_snapshots", ["score_combined"])
    op.create_index("ix_score_snapshots_severity", "score_snapshots", ["severity"])
    op.create_index("ix_score_snapshots_created_at", "score_snapshots", ["created_at"])
    op.create_index("ix_score_snapshots_model_version", "score_snapshots", ["model_version"])

    op.create_table(
        "explanation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score_snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("score_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_explanation_records_user_id", "explanation_records", ["user_id"])
    op.create_index("ix_explanation_records_score_snapshot_id", "explanation_records", ["score_snapshot_id"])
    op.create_index("ix_explanation_records_finding_id", "explanation_records", ["finding_id"])

    for table in ("identity_edges", "identity_collisions", "score_snapshots", "explanation_records"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute("CREATE POLICY identity_edges_self ON identity_edges FOR ALL USING (user_id::text = current_setting('app.current_user_id', true)) WITH CHECK (user_id::text = current_setting('app.current_user_id', true));")
    op.execute("CREATE POLICY identity_collisions_self ON identity_collisions FOR ALL USING (user_id::text = current_setting('app.current_user_id', true)) WITH CHECK (user_id::text = current_setting('app.current_user_id', true));")
    op.execute("CREATE POLICY score_snapshots_self ON score_snapshots FOR ALL USING (user_id::text = current_setting('app.current_user_id', true)) WITH CHECK (user_id::text = current_setting('app.current_user_id', true));")
    op.execute("CREATE POLICY explanation_records_self ON explanation_records FOR ALL USING (user_id::text = current_setting('app.current_user_id', true)) WITH CHECK (user_id::text = current_setting('app.current_user_id', true));")


def downgrade() -> None:
    for pol, tbl in [
        ("explanation_records_self", "explanation_records"),
        ("score_snapshots_self", "score_snapshots"),
        ("identity_collisions_self", "identity_collisions"),
        ("identity_edges_self", "identity_edges"),
    ]:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {tbl}")
    for table in ("explanation_records", "score_snapshots", "identity_collisions", "identity_edges"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
