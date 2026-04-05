"""add profile contact methods and visibility

Revision ID: 20260405_0013
Revises: 20260405_0012
Create Date: 2026-04-05 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260405_0013"
down_revision = "20260405_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("contact_methods_json", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("contact_visibility", sa.String(length=16), nullable=False, server_default="all"))
    op.add_column("user_profiles", sa.Column("contact_visibility_method_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "contact_visibility_method_id")
    op.drop_column("user_profiles", "contact_visibility")
    op.drop_column("user_profiles", "contact_methods_json")
