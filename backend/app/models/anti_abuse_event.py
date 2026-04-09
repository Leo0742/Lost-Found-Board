from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AntiAbuseEvent(Base):
    __tablename__ = "anti_abuse_events"
    __table_args__ = (
        Index("ix_anti_abuse_events_created_at_id", "created_at", "id"),
        Index("ix_anti_abuse_events_action_created", "action", "created_at"),
        Index("ix_anti_abuse_events_item_created", "item_id", "created_at"),
        Index("ix_anti_abuse_events_blocked_created", "blocked", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    fingerprint: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
