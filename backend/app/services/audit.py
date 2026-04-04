from datetime import datetime

from datetime import UTC, timedelta

from sqlalchemy import Select, delete, select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent

EVENT_LABELS = {
    "item_created": "Report created",
    "item_updated": "Report updated",
    "item_deleted": "Report deleted",
    "item_resolved": "Report resolved",
    "item_reopened": "Report reopened",
    "item_flagged": "Public abuse flag",
    "item_moderated": "Moderation decision",
    "item_verification_changed": "Verification changed",
    "claim_created": "Claim created",
    "claim_status_changed": "Claim status changed",
}


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
    query = query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).offset(offset).limit(limit)
    return list(db.scalars(query).all())


def cleanup_expired_events(
    db: Session,
    *,
    retention_days: int,
    batch_size: int = 2000,
    max_batches: int = 50,
) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    total_removed = 0
    batches = 0
    while batches < max_batches:
        expired_ids = list(
            db.scalars(
                select(AuditEvent.id)
                .where(AuditEvent.created_at < cutoff)
                .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
                .limit(batch_size)
            )
        )
        if not expired_ids:
            break
        result = db.execute(delete(AuditEvent).where(AuditEvent.id.in_(expired_ids)))
        db.commit()
        total_removed += result.rowcount or 0
        batches += 1
        if len(expired_ids) < batch_size:
            break
    return total_removed


def describe_event(event: AuditEvent) -> dict:
    label = EVENT_LABELS.get(event.event_type, event.event_type.replace("_", " ").title())
    summary = label
    if event.event_type == "item_moderated":
        action = (event.details or {}).get("action")
        if action:
            summary = f"{label}: {action}"
    elif event.event_type == "claim_status_changed":
        status = (event.details or {}).get("status")
        if status:
            summary = f"{label}: {status}"
    elif event.event_type == "item_flagged":
        reason = (event.details or {}).get("normalized_reason") or (event.details or {}).get("reason")
        if reason:
            summary = f"{label}: {reason}"

    return {
        "label": label,
        "summary": summary,
        "item_url": f"/admin?item_id={event.item_id}" if event.item_id else None,
        "claim_url": f"/admin?claim_id={event.claim_id}" if event.claim_id else None,
    }
