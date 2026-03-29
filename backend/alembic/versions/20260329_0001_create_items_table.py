"""create items table

Revision ID: 20260329_0001
Revises:
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260329_0001"
down_revision = None
branch_labels = None
depends_on = None


# Enum type is created/dropped explicitly in this migration.
# create_type=False prevents a second implicit CREATE TYPE when creating the table.
status_enum = sa.Enum("lost", "found", name="item_status", create_type=False)


def upgrade() -> None:
    status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("contact_name", sa.String(length=80), nullable=False),
        sa.Column("telegram_username", sa.String(length=80), nullable=True),
        sa.Column("telegram_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_items_id", "items", ["id"])


def downgrade() -> None:
    op.drop_index("ix_items_id", table_name="items")
    op.drop_table("items")
    status_enum.drop(op.get_bind(), checkfirst=True)
