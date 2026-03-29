"""add item lifecycle fields

Revision ID: 20260329_0002
Revises: 20260329_0001
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_0002"
down_revision = "20260329_0001"
branch_labels = None
depends_on = None


lifecycle_enum = postgresql.ENUM("active", "resolved", "deleted", name="item_lifecycle", create_type=False)


def upgrade() -> None:
    lifecycle_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "items",
        sa.Column("lifecycle", lifecycle_enum, nullable=False, server_default="active"),
    )
    op.add_column("items", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("items", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("items", "lifecycle", server_default=None)


def downgrade() -> None:
    op.drop_column("items", "deleted_at")
    op.drop_column("items", "resolved_at")
    op.drop_column("items", "lifecycle")
    lifecycle_enum.drop(op.get_bind(), checkfirst=True)
