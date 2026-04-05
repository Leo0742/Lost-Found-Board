"""add telegram avatar to profiles

Revision ID: 20260405_0012
Revises: 20260405_0011
Create Date: 2026-04-05 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260405_0012"
down_revision = "20260405_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("telegram_avatar_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "telegram_avatar_url")
