"""add user profiles table

Revision ID: 20260405_0011
Revises: 20260404_0010
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa


revision = "20260405_0011"
down_revision = "20260404_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_user_id", sa.Integer(), nullable=False),
        sa.Column("telegram_username", sa.String(length=80), nullable=True),
        sa.Column("telegram_display_name", sa.String(length=120), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("preferred_contact_method", sa.String(length=32), nullable=True),
        sa.Column("preferred_contact_details", sa.String(length=255), nullable=True),
        sa.Column("pickup_location", sa.String(length=160), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("telegram_user_id", name="uq_user_profiles_telegram_user_id"),
    )
    op.create_index("ix_user_profiles_id", "user_profiles", ["id"])
    op.create_index("ix_user_profiles_telegram_user_id", "user_profiles", ["telegram_user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_profiles_telegram_user_id", table_name="user_profiles")
    op.drop_index("ix_user_profiles_id", table_name="user_profiles")
    op.drop_table("user_profiles")
