"""add anti abuse events

Revision ID: 20260404_0009
Revises: 20260404_0008
Create Date: 2026-04-04 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_0009"
down_revision = "20260404_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "anti_abuse_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("actor_telegram_user_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(length=64), nullable=True),
        sa.Column("ip_hash", sa.String(length=64), nullable=True),
        sa.Column("fingerprint", sa.String(length=120), nullable=True),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_anti_abuse_events_action"), "anti_abuse_events", ["action"], unique=False)
    op.create_index(op.f("ix_anti_abuse_events_actor_telegram_user_id"), "anti_abuse_events", ["actor_telegram_user_id"], unique=False)
    op.create_index(op.f("ix_anti_abuse_events_session_id"), "anti_abuse_events", ["session_id"], unique=False)
    op.create_index(op.f("ix_anti_abuse_events_ip_hash"), "anti_abuse_events", ["ip_hash"], unique=False)
    op.create_index(op.f("ix_anti_abuse_events_fingerprint"), "anti_abuse_events", ["fingerprint"], unique=False)
    op.create_index(op.f("ix_anti_abuse_events_item_id"), "anti_abuse_events", ["item_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_anti_abuse_events_item_id"), table_name="anti_abuse_events")
    op.drop_index(op.f("ix_anti_abuse_events_fingerprint"), table_name="anti_abuse_events")
    op.drop_index(op.f("ix_anti_abuse_events_ip_hash"), table_name="anti_abuse_events")
    op.drop_index(op.f("ix_anti_abuse_events_session_id"), table_name="anti_abuse_events")
    op.drop_index(op.f("ix_anti_abuse_events_actor_telegram_user_id"), table_name="anti_abuse_events")
    op.drop_index(op.f("ix_anti_abuse_events_action"), table_name="anti_abuse_events")
    op.drop_table("anti_abuse_events")
