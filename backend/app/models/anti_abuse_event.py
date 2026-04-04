from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AntiAbuseEvent(Base):
    __tablename__ = "anti_abuse_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_telegram_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    fingerprint: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
