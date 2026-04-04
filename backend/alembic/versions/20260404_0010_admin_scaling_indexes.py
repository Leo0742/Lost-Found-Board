"""add admin scaling indexes

Revision ID: 20260404_0010
Revises: 20260404_0009
Create Date: 2026-04-04 00:30:00.000000
"""

from alembic import op


revision = "20260404_0010"
down_revision = "20260404_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_audit_events_created_at_id", "audit_events", ["created_at", "id"], unique=False)
    op.create_index("ix_audit_events_event_created", "audit_events", ["event_type", "created_at"], unique=False)
    op.create_index("ix_audit_events_item_created", "audit_events", ["item_id", "created_at"], unique=False)
    op.create_index("ix_audit_events_claim_created", "audit_events", ["claim_id", "created_at"], unique=False)
    op.create_index("ix_audit_events_actor_created", "audit_events", ["actor_telegram_user_id", "created_at"], unique=False)

    op.create_index("ix_anti_abuse_events_created_at_id", "anti_abuse_events", ["created_at", "id"], unique=False)
    op.create_index("ix_anti_abuse_events_action_created", "anti_abuse_events", ["action", "created_at"], unique=False)
    op.create_index("ix_anti_abuse_events_item_created", "anti_abuse_events", ["item_id", "created_at"], unique=False)
    op.create_index("ix_anti_abuse_events_blocked_created", "anti_abuse_events", ["blocked", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_anti_abuse_events_blocked_created", table_name="anti_abuse_events")
    op.drop_index("ix_anti_abuse_events_item_created", table_name="anti_abuse_events")
    op.drop_index("ix_anti_abuse_events_action_created", table_name="anti_abuse_events")
    op.drop_index("ix_anti_abuse_events_created_at_id", table_name="anti_abuse_events")

    op.drop_index("ix_audit_events_actor_created", table_name="audit_events")
    op.drop_index("ix_audit_events_claim_created", table_name="audit_events")
    op.drop_index("ix_audit_events_item_created", table_name="audit_events")
    op.drop_index("ix_audit_events_event_created", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at_id", table_name="audit_events")
