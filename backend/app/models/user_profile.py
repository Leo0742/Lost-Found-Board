from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    telegram_display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    preferred_contact_method: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preferred_contact_details: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pickup_location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    telegram_avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
