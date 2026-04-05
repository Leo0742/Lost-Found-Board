"""add claim live meetup locations

Revision ID: 20260405_0015
Revises: 20260405_0014
Create Date: 2026-04-05 13:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_0015"
down_revision = "20260405_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("live_location_json", sa.Text(), nullable=True))
    op.add_column("claims", sa.Column("live_location_shared_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("claims", sa.Column("live_location_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("claims", "live_location_expires_at")
    op.drop_column("claims", "live_location_shared_at")
    op.drop_column("claims", "live_location_json")
