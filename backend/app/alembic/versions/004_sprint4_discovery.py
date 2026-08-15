"""sprint4_discovery_evidence

Revision ID: 004_sprint4_discovery
Revises: 003_sprint3_connectors
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_sprint4_discovery"
down_revision: str | None = "003_sprint3_connectors"  # ← set to your Sprint 3 rev
branch_labels = None
depends_on = None


def upgrade() -> None:
    # scans
    op.create_table(
        "scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("layer_scope", sa.String(32), nullable=False, server_default="surface"),
        sa.Column("connector_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("progress_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("message", sa.String(512), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finding_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_scans_user_id", "scans", ["user_id"])
    op.create_index("ix_scans_identifier_id", "scans", ["identifier_id"])
    op.create_index("ix_scans_status", "scans", ["status"])

    # scan_connector_runs
    op.create_table(
        "scan_connector_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connector_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("skip_reason", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finding_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("scan_id", "connector_id", name="uq_scan_connector_run"),
    )
    op.create_index("ix_scan_connector_runs_scan_id", "scan_connector_runs", ["scan_id"])
    op.create_index("ix_scan_connector_runs_user_id", "scan_connector_runs", ["user_id"])
    op.create_index("ix_scan_connector_runs_status", "scan_connector_runs", ["status"])
    op.create_index("ix_scan_connector_runs_connector_id", "scan_connector_runs", ["connector_id"])

    # observations
    op.create_table(
        "observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("connector_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scan_connector_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("layer", sa.String(32), nullable=False, server_default="surface"),
        sa.Column("raw_ref", sa.String(512), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attribution", sa.String(512), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_observations_user_id", "observations", ["user_id"])
    op.create_index("ix_observations_identifier_id", "observations", ["identifier_id"])
    op.create_index("ix_observations_scan_id", "observations", ["scan_id"])
    op.create_index("ix_observations_source", "observations", ["source"])
    op.create_index("ix_observations_expires_at", "observations", ["expires_at"])
    op.create_index("ix_observations_kind", "observations", ["kind"])

    # findings
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("severity_hint", sa.String(32), nullable=False, server_default="info"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("layer", sa.String(32), nullable=False, server_default="surface"),
        sa.Column("track", sa.String(32), nullable=False, server_default="confirmed"),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("raw_ref", sa.String(512), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("attribution", sa.String(512), nullable=True),
        sa.Column("first_seen_scan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_seen_scan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("times_seen", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "identifier_id", "source", "fingerprint", name="uq_findings_user_ident_source_fp"),
    )
    op.create_index("ix_findings_user_id", "findings", ["user_id"])
    op.create_index("ix_findings_identifier_id", "findings", ["identifier_id"])
    op.create_index("ix_findings_kind", "findings", ["kind"])
    op.create_index("ix_findings_source", "findings", ["source"])
    op.create_index("ix_findings_severity_hint", "findings", ["severity_hint"])
    op.create_index("ix_findings_layer", "findings", ["layer"])
    op.create_index("ix_findings_status", "findings", ["status"])
    op.create_index("ix_findings_raw_ref", "findings", ["raw_ref"])

    # evidence_blobs
    op.create_table(
        "evidence_blobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("findings.id", ondelete="CASCADE"), nullable=True),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("layer", sa.String(16), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False, server_default="application/json"),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_evidence_blobs_user_id", "evidence_blobs", ["user_id"])
    op.create_index("ix_evidence_blobs_identifier_id", "evidence_blobs", ["identifier_id"])
    op.create_index("ix_evidence_blobs_scan_id", "evidence_blobs", ["scan_id"])
    op.create_index("ix_evidence_blobs_finding_id", "evidence_blobs", ["finding_id"])
    op.create_index("ix_evidence_blobs_layer", "evidence_blobs", ["layer"])
    op.create_index("ix_evidence_blobs_expires_at", "evidence_blobs", ["expires_at"])

    # ---------- RLS ----------
    for table in ("scans", "scan_connector_runs", "observations", "findings", "evidence_blobs"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY scans_self ON scans
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY scan_runs_self ON scan_connector_runs
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY observations_self ON observations
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY findings_self ON findings
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY evidence_self ON evidence_blobs
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)

    # ---------- ACTIVATE verified-only G1 triggers (function from Sprint 2) ----------
    # Ensure function exists (idempotent recreate)
    op.execute("""
        CREATE OR REPLACE FUNCTION digizafe_enforce_verified_identifier()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_ok boolean;
        BEGIN
            SELECT is_verified INTO v_ok
            FROM identifiers
            WHERE id = NEW.identifier_id;

            IF v_ok IS DISTINCT FROM TRUE THEN
                RAISE EXCEPTION 'G1_VIOLATION: only verified identifiers allowed (identifier_id=%)',
                    NEW.identifier_id
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)

    op.execute("DROP TRIGGER IF EXISTS trg_scans_verified_only ON scans;")
    op.execute("""
        CREATE TRIGGER trg_scans_verified_only
            BEFORE INSERT OR UPDATE OF identifier_id ON scans
            FOR EACH ROW EXECUTE FUNCTION digizafe_enforce_verified_identifier();
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_observations_verified_only ON observations;")
    op.execute("""
        CREATE TRIGGER trg_observations_verified_only
            BEFORE INSERT OR UPDATE OF identifier_id ON observations
            FOR EACH ROW EXECUTE FUNCTION digizafe_enforce_verified_identifier();
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_findings_verified_only ON findings;")
    op.execute("""
        CREATE TRIGGER trg_findings_verified_only
            BEFORE INSERT OR UPDATE OF identifier_id ON findings
            FOR EACH ROW EXECUTE FUNCTION digizafe_enforce_verified_identifier();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_findings_verified_only ON findings")
    op.execute("DROP TRIGGER IF EXISTS trg_observations_verified_only ON observations")
    op.execute("DROP TRIGGER IF EXISTS trg_scans_verified_only ON scans")
    # keep function — may be shared

    for pol, tbl in [
        ("evidence_self", "evidence_blobs"),
        ("findings_self", "findings"),
        ("observations_self", "observations"),
        ("scan_runs_self", "scan_connector_runs"),
        ("scans_self", "scans"),
    ]:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {tbl}")

    for table in ("evidence_blobs", "findings", "observations", "scan_connector_runs", "scans"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_table("evidence_blobs")
    op.drop_table("findings")
    op.drop_table("observations")
    op.drop_table("scan_connector_runs")
    op.drop_table("scans")
