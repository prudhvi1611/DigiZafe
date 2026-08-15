"""sprint2_identifiers_verification_egress"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_sprint2_identifiers"
down_revision: str | None = "001_sprint1_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("value_canonical", sa.String(512), nullable=False),
        sa.Column("value_display", sa.String(512), nullable=False),
        sa.Column("value_blind", sa.String(64), nullable=True),
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_method", sa.String(64), nullable=True),
        sa.Column("last_revalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "type", "value_canonical", name="uq_identifiers_user_type_value"),
    )
    op.create_index("ix_identifiers_user_id", "identifiers", ["user_id"])
    op.create_index("ix_identifiers_type", "identifiers", ["type"])
    op.create_index("ix_identifiers_value_canonical", "identifiers", ["value_canonical"])
    op.create_index("ix_identifiers_is_verified", "identifiers", ["is_verified"])
    op.create_index("ix_identifiers_value_blind", "identifiers", ["value_blind"])

    op.create_table(
        "verification_challenges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("identifiers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("secret_hash", sa.String(128), nullable=False),
        sa.Column("public_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_verification_challenges_identifier_id", "verification_challenges", ["identifier_id"])
    op.create_index("ix_verification_challenges_user_id", "verification_challenges", ["user_id"])

    op.create_table(
        "consent_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(128), nullable=False),
        sa.Column("scope", sa.String(256), nullable=True),
        sa.Column("granted", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_consent_records_user_id", "consent_records", ["user_id"])
    op.create_index("ix_consent_records_purpose", "consent_records", ["purpose"])

    op.create_table(
        "egress_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("identifier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("purpose", sa.String(128), nullable=False),
        sa.Column("destination_host", sa.String(255), nullable=False),
        sa.Column("method", sa.String(16), server_default="GET", nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_egress_ledger_user_id", "egress_ledger", ["user_id"])
    op.create_index("ix_egress_ledger_identifier_id", "egress_ledger", ["identifier_id"])
    op.create_index("ix_egress_ledger_purpose", "egress_ledger", ["purpose"])
    op.create_index("ix_egress_ledger_created_at", "egress_ledger", ["created_at"])
    op.create_index("ix_egress_ledger_correlation_id", "egress_ledger", ["correlation_id"])

    # RLS
    for table in ("identifiers", "verification_challenges", "consent_records", "egress_ledger"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY identifiers_self ON identifiers
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    # Allow insert when setting is present (request path sets it after auth)
    op.execute("""
        CREATE POLICY verification_challenges_self ON verification_challenges
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY consent_self ON consent_records
        FOR ALL
        USING (user_id::text = current_setting('app.current_user_id', true))
        WITH CHECK (user_id::text = current_setting('app.current_user_id', true));
    """)
    op.execute("""
        CREATE POLICY egress_self_select ON egress_ledger
        FOR SELECT
        USING (
            user_id IS NULL
            OR user_id::text = current_setting('app.current_user_id', true)
        );
    """)
    op.execute("""
        CREATE POLICY egress_insert ON egress_ledger
        FOR INSERT
        WITH CHECK (true);
    """)

    # ---------- Verified-only trigger DESIGN (ready for Sprint 4 scan tables) ----------
    # Function lives now; trigger attaches when observations/findings/scans exist.
    op.execute("""
        CREATE OR REPLACE FUNCTION digizafe_enforce_verified_identifier()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_ok boolean;
        BEGIN
            -- Expect NEW.identifier_id to reference identifiers(id)
            SELECT is_verified INTO v_ok
            FROM identifiers
            WHERE id = NEW.identifier_id;

            IF v_ok IS DISTINCT FROM TRUE THEN
                RAISE EXCEPTION 'G1_VIOLATION: scans/findings only allowed for verified identifiers (identifier_id=%)',
                    NEW.identifier_id
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    # Example (commented until scans table exists in Sprint 4):
    # CREATE TRIGGER trg_scans_verified_only
    #   BEFORE INSERT OR UPDATE ON scans
    #   FOR EACH ROW EXECUTE FUNCTION digizafe_enforce_verified_identifier();


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS digizafe_enforce_verified_identifier() CASCADE")
    for pol, tbl in [
        ("egress_insert", "egress_ledger"),
        ("egress_self_select", "egress_ledger"),
        ("consent_self", "consent_records"),
        ("verification_challenges_self", "verification_challenges"),
        ("identifiers_self", "identifiers"),
    ]:
        op.execute(f"DROP POLICY IF EXISTS {pol} ON {tbl}")
    for table in ("egress_ledger", "consent_records", "verification_challenges", "identifiers"):
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
