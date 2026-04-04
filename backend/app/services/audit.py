from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def log_event(
    db: Session,
    event_type: str,
    *,
    actor_telegram_user_id: int | None = None,
    item_id: int | None = None,
    claim_id: int | None = None,
    details: dict | None = None,
) -> None:
    event = AuditEvent(
        event_type=event_type,
        actor_telegram_user_id=actor_telegram_user_id,
        item_id=item_id,
        claim_id=claim_id,
        details=details or {},
    )
    db.add(event)


def list_events(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
    actor_telegram_user_id: int | None = None,
    item_id: int | None = None,
    claim_id: int | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[AuditEvent]:
    query: Select[tuple[AuditEvent]] = select(AuditEvent)
    if event_type:
        query = query.where(AuditEvent.event_type == event_type)
    if actor_telegram_user_id is not None:
        query = query.where(AuditEvent.actor_telegram_user_id == actor_telegram_user_id)
    if item_id is not None:
        query = query.where(AuditEvent.item_id == item_id)
    if claim_id is not None:
        query = query.where(AuditEvent.claim_id == claim_id)
    if created_from is not None:
        query = query.where(AuditEvent.created_at >= created_from)
    if created_to is not None:
        query = query.where(AuditEvent.created_at <= created_to)
    query = query.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit)
    return list(db.scalars(query).all())
