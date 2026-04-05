"""add profile addresses and visibility

Revision ID: 20260405_0014
Revises: 20260405_0013
Create Date: 2026-04-05 12:30:00.000000
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = "20260405_0014"
down_revision = "20260405_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("profile_addresses_json", sa.Text(), nullable=True))
    op.add_column("user_profiles", sa.Column("address_visibility", sa.String(length=16), nullable=False, server_default="all"))
    op.add_column("user_profiles", sa.Column("address_visibility_address_id", sa.String(length=64), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(text("SELECT id, pickup_location FROM user_profiles WHERE pickup_location IS NOT NULL AND btrim(pickup_location) <> ''"))
    for row in rows:
        payload = [
            {
                "id": "legacy-primary",
                "label": "Primary",
                "address_text": row.pickup_location.strip()[:255],
                "latitude": None,
                "longitude": None,
                "extra_details": None,
            }
        ]
        bind.execute(
            text("UPDATE user_profiles SET profile_addresses_json = :payload WHERE id = :profile_id"),
            {"payload": json.dumps(payload, ensure_ascii=False), "profile_id": row.id},
        )


def downgrade() -> None:
    op.drop_column("user_profiles", "address_visibility_address_id")
    op.drop_column("user_profiles", "address_visibility")
    op.drop_column("user_profiles", "profile_addresses_json")
