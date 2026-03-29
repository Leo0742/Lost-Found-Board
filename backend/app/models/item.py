from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ItemStatus(str, Enum):
    LOST = "lost"
    FOUND = "found"


class ItemLifecycle(str, Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    DELETED = "deleted"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False, default="Other")
    location: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[ItemStatus] = mapped_column(
        SqlEnum(
            ItemStatus,
            name="item_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
    )
    lifecycle: Mapped[ItemLifecycle] = mapped_column(
        SqlEnum(
            ItemLifecycle,
            name="item_lifecycle",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
            validate_strings=True,
        ),
        nullable=False,
        default=ItemLifecycle.ACTIVE,
    )
    contact_name: Mapped[str] = mapped_column(String(80), nullable=False)
    telegram_username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    telegram_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
