"""add audit events

Revision ID: 20260404_0007
Revises: 20260329_0006
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa

revision = "20260404_0007"
down_revision = "20260329_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_telegram_user_id", sa.Integer(), nullable=True),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("claim_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_actor_telegram_user_id", "audit_events", ["actor_telegram_user_id"])
    op.create_index("ix_audit_events_item_id", "audit_events", ["item_id"])
    op.create_index("ix_audit_events_claim_id", "audit_events", ["claim_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_claim_id", table_name="audit_events")
    op.drop_index("ix_audit_events_item_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_telegram_user_id", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_table("audit_events")
