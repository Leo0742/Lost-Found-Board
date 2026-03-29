"""create claims table

Revision ID: 20260329_0005
Revises: 20260329_0004
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_0005"
down_revision = "20260329_0004"
branch_labels = None
depends_on = None

claim_status_enum = postgresql.ENUM(
    "pending", "approved", "rejected", "cancelled", "completed", "not_match", name="claim_status", create_type=False
)


def upgrade() -> None:
    claim_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_item_id", sa.Integer(), sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requester_telegram_user_id", sa.Integer(), nullable=True),
        sa.Column("owner_telegram_user_id", sa.Integer(), nullable=True),
        sa.Column("requester_name", sa.String(length=120), nullable=True),
        sa.Column("claim_message", sa.Text(), nullable=True),
        sa.Column("status", claim_status_enum, nullable=False, server_default="pending"),
        sa.Column("handoff_note", sa.String(length=255), nullable=True),
        sa.Column("resolved_by_claim", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_claims_id", "claims", ["id"])


def downgrade() -> None:
    op.drop_index("ix_claims_id", table_name="claims")
    op.drop_table("claims")
    claim_status_enum.drop(op.get_bind(), checkfirst=True)
