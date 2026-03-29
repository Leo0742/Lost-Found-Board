from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WebAuthSession(Base):
    __tablename__ = "web_auth_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    link_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True, index=True)
    telegram_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    telegram_username: Mapped[str | None] = mapped_column(String(80), nullable=True)
    telegram_display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    link_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
