"""add moderation and verification fields

Revision ID: 20260329_0004
Revises: 20260329_0003
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_0004"
down_revision = "20260329_0003"
branch_labels = None
depends_on = None

moderation_enum = postgresql.ENUM("pending", "approved", "rejected", "flagged", name="moderation_status", create_type=False)


def upgrade() -> None:
    moderation_enum.create(op.get_bind(), checkfirst=True)
    op.add_column("items", sa.Column("moderation_status", moderation_enum, nullable=False, server_default="approved"))
    op.add_column("items", sa.Column("moderation_reason", sa.String(length=255), nullable=True))
    op.add_column("items", sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("items", sa.Column("moderated_by", sa.String(length=120), nullable=True))
    op.add_column("items", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("items", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("items", "moderation_status", server_default=None)
    op.alter_column("items", "is_verified", server_default=None)


def downgrade() -> None:
    op.drop_column("items", "verified_at")
    op.drop_column("items", "is_verified")
    op.drop_column("items", "moderated_by")
    op.drop_column("items", "moderated_at")
    op.drop_column("items", "moderation_reason")
    op.drop_column("items", "moderation_status")
    moderation_enum.drop(op.get_bind(), checkfirst=True)
