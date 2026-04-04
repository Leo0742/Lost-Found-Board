"""add csrf token to web sessions

Revision ID: 20260404_0008
Revises: 20260404_0007
Create Date: 2026-04-04 00:00:08
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260404_0008"
down_revision = "20260404_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("web_auth_sessions", sa.Column("csrf_token", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("web_auth_sessions", "csrf_token")
