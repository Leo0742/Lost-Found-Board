from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_created_at_id", "created_at", "id"),
        Index("ix_audit_events_event_created", "event_type", "created_at"),
        Index("ix_audit_events_item_created", "item_id", "created_at"),
        Index("ix_audit_events_claim_created", "claim_id", "created_at"),
        Index("ix_audit_events_actor_created", "actor_telegram_user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_telegram_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    item_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    claim_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
