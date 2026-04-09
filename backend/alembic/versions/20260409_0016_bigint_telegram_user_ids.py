"""bigint telegram user ids

Telegram user IDs can exceed the 32-bit signed integer range (max ~2.1 billion).
IDs such as 8457445258 already exist in the wild and caused
  psycopg.errors.NumericValueOutOfRange: integer out of range
on the /api/auth/link/confirm endpoint.

Alter every column that stores a Telegram user ID from INTEGER to BIGINT.

Revision ID: 20260409_0016
Revises: 20260405_0015
Create Date: 2026-04-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260409_0016"
down_revision = "20260405_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # anti_abuse_events
    op.alter_column(
        "anti_abuse_events",
        "actor_telegram_user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )

    # audit_events
    op.alter_column(
        "audit_events",
        "actor_telegram_user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )

    # web_auth_sessions
    op.alter_column(
        "web_auth_sessions",
        "telegram_user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )

    # user_profiles
    op.alter_column(
        "user_profiles",
        "telegram_user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )

    # items (two columns)
    op.alter_column(
        "items",
        "telegram_user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )
    op.alter_column(
        "items",
        "owner_telegram_user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )

    # claims (two columns)
    op.alter_column(
        "claims",
        "requester_telegram_user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )
    op.alter_column(
        "claims",
        "owner_telegram_user_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # Revert all columns back to INTEGER.
    # NOTE: this will fail if any stored value exceeds 2^31-1.

    op.alter_column(
        "claims",
        "owner_telegram_user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "claims",
        "requester_telegram_user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "items",
        "owner_telegram_user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "items",
        "telegram_user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "user_profiles",
        "telegram_user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "web_auth_sessions",
        "telegram_user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "audit_events",
        "actor_telegram_user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
    op.alter_column(
        "anti_abuse_events",
        "actor_telegram_user_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )
