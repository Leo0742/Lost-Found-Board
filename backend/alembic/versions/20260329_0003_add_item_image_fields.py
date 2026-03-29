"""add item image fields

Revision ID: 20260329_0003
Revises: 20260329_0002
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260329_0003"
down_revision = "20260329_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("items", sa.Column("image_path", sa.String(length=255), nullable=True))
    op.add_column("items", sa.Column("image_filename", sa.String(length=255), nullable=True))
    op.add_column("items", sa.Column("image_mime_type", sa.String(length=120), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "image_mime_type")
    op.drop_column("items", "image_filename")
    op.drop_column("items", "image_path")
