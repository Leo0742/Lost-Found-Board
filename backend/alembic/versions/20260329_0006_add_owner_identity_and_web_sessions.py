"""add owner identity and web auth sessions

Revision ID: 20260329_0006
Revises: 20260329_0005
Create Date: 2026-03-29 00:40:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260329_0006"
down_revision: str | None = "20260329_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("items", sa.Column("owner_telegram_user_id", sa.Integer(), nullable=True))
    op.add_column("items", sa.Column("owner_telegram_username", sa.String(length=80), nullable=True))
    op.add_column("items", sa.Column("owner_display_name", sa.String(length=120), nullable=True))
    op.create_index("ix_items_owner_telegram_user_id", "items", ["owner_telegram_user_id"])

    op.execute(
        """
        UPDATE items
        SET owner_telegram_user_id = telegram_user_id,
            owner_telegram_username = telegram_username,
            owner_display_name = contact_name
        WHERE owner_telegram_user_id IS NULL
        """
    )

    op.create_table(
        "web_auth_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("link_code", sa.String(length=16), nullable=True),
        sa.Column("telegram_user_id", sa.Integer(), nullable=True),
        sa.Column("telegram_username", sa.String(length=80), nullable=True),
        sa.Column("telegram_display_name", sa.String(length=120), nullable=True),
        sa.Column("link_code_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_web_auth_sessions_link_code", "web_auth_sessions", ["link_code"], unique=True)
    op.create_index("ix_web_auth_sessions_telegram_user_id", "web_auth_sessions", ["telegram_user_id"])


def downgrade() -> None:
    op.drop_index("ix_web_auth_sessions_telegram_user_id", table_name="web_auth_sessions")
    op.drop_index("ix_web_auth_sessions_link_code", table_name="web_auth_sessions")
    op.drop_table("web_auth_sessions")

    op.drop_index("ix_items_owner_telegram_user_id", table_name="items")
    op.drop_column("items", "owner_display_name")
    op.drop_column("items", "owner_telegram_username")
    op.drop_column("items", "owner_telegram_user_id")
