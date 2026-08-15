"""sprint3_connector_configs"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_sprint3_connectors"
down_revision: str | None = "002_sprint2_identifiers"  # your Sprint 2 rev
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "connector_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("connector_id", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_connector_configs_connector_id", "connector_configs", ["connector_id"], unique=True)

    # Seed defaults (all enabled)
    # Optional raw SQL inserts — app works without rows (env flags apply)


def downgrade() -> None:
    op.drop_table("connector_configs")
