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
