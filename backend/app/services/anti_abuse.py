from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
import hashlib

from fastapi import HTTPException, Request
from sqlalchemy import Select, delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.anti_abuse_event import AntiAbuseEvent


@dataclass(frozen=True)
class RateLimitRule:
    window_seconds: int
    max_hits: int
    error_message: str


class AbuseClass(StrEnum):
    RATE_LIMIT = "rate_limit"
    DUPLICATE = "duplicate"
    SIGNAL = "signal"


class AbuseAction(StrEnum):
    CREATE_ITEM = "create_item"
    CREATE_ITEM_ANON = "create_item_anon"
    UPLOAD_IMAGE = "upload_image"
    SMART_SEARCH = "smart_search"
    CATEGORY_SUGGEST = "category_suggest"
    FLAG_ITEM = "flag_item"
    FLAG_SUBMISSION = "flag_item_submission"
    FLAG_DUPLICATE = "flag_item_duplicate"
    CREATE_CLAIM = "create_claim"
    CLAIM_SUBMISSION = "claim_submission"
    CLAIM_DUPLICATE = "claim_duplicate"
    ADMIN_AUDIT_LIST = "admin_audit_list"


def client_ip_hash(request: Request | None) -> str | None:
    if not request:
        return None
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else "")
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:32]


def normalize_reason(reason: str) -> str:
    normalized = " ".join(reason.lower().split())
    aliases = {
        "spam": "spam_or_scam",
        "scam": "spam_or_scam",
        "fraud": "spam_or_scam",
        "duplicate": "duplicate_or_repeat",
        "dupe": "duplicate_or_repeat",
        "fake": "fake_or_misleading",
        "misleading": "fake_or_misleading",
        "unsafe": "abusive_or_unsafe",
        "abusive": "abusive_or_unsafe",
        "wrong category": "wrong_category",
        "wrong_category": "wrong_category",
    }
    return aliases.get(normalized, normalized)


def _identity_filter(actor_telegram_user_id: int | None, session_id: str | None, ip_hash: str | None):
    options = []
    if actor_telegram_user_id is not None:
        options.append(AntiAbuseEvent.actor_telegram_user_id == actor_telegram_user_id)
    if session_id:
        options.append(AntiAbuseEvent.session_id == session_id)
    if ip_hash:
        options.append(AntiAbuseEvent.ip_hash == ip_hash)
    if not options:
        return None
    return or_(*options)


def enforce_rate_limit(
    db: Session,
    *,
    action: str,
    rule: RateLimitRule,
    actor_telegram_user_id: int | None,
    session_id: str | None,
    ip_hash: str | None,
    fingerprint: str | None = None,
    item_id: int | None = None,
) -> None:
    now = datetime.now(UTC)
    since = now - timedelta(seconds=rule.window_seconds)

    query: Select[tuple[int]] = select(func.count(AntiAbuseEvent.id)).where(
        AntiAbuseEvent.action == action,
        AntiAbuseEvent.created_at >= since,
        AntiAbuseEvent.blocked.is_(False),
    )
    identity = _identity_filter(actor_telegram_user_id, session_id, ip_hash)
    if identity is not None:
        query = query.where(identity)
    if fingerprint:
        query = query.where(AntiAbuseEvent.fingerprint == fingerprint)
    if item_id is not None:
        query = query.where(AntiAbuseEvent.item_id == item_id)

    recent = db.scalar(query) or 0
    blocked = recent >= rule.max_hits
    db.add(
        AntiAbuseEvent(
            action=action,
            actor_telegram_user_id=actor_telegram_user_id,
            session_id=session_id,
            ip_hash=ip_hash,
            fingerprint=fingerprint,
            item_id=item_id,
            blocked=blocked,
        )
    )
    db.commit()
    if blocked:
        raise HTTPException(status_code=429, detail=rule.error_message)


def record_signal(
    db: Session,
    *,
    action: str,
    actor_telegram_user_id: int | None,
    session_id: str | None,
    ip_hash: str | None,
    fingerprint: str | None = None,
    item_id: int | None = None,
) -> None:
    db.add(
        AntiAbuseEvent(
            action=action,
            actor_telegram_user_id=actor_telegram_user_id,
            session_id=session_id,
            ip_hash=ip_hash,
            fingerprint=fingerprint,
            item_id=item_id,
            blocked=False,
        )
    )


def has_recent_duplicate(
    db: Session,
    *,
    action: str,
    actor_telegram_user_id: int | None,
    session_id: str | None,
    ip_hash: str | None,
    fingerprint: str,
    item_id: int | None,
    within_hours: int,
) -> bool:
    since = datetime.now(UTC) - timedelta(hours=within_hours)
    query = select(AntiAbuseEvent.id).where(
        AntiAbuseEvent.action == action,
        AntiAbuseEvent.created_at >= since,
        AntiAbuseEvent.fingerprint == fingerprint,
        AntiAbuseEvent.blocked.is_(False),
    )
    if item_id is not None:
        query = query.where(AntiAbuseEvent.item_id == item_id)
    identity = _identity_filter(actor_telegram_user_id, session_id, ip_hash)
    if identity is not None:
        query = query.where(identity)
    return db.scalar(query.limit(1)) is not None


def cleanup_expired_events(db: Session, *, retention_days: int, batch_size: int = 2000) -> int:
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    total_removed = 0
    while True:
        expired_ids = list(
            db.scalars(
                select(AntiAbuseEvent.id)
                .where(AntiAbuseEvent.created_at < cutoff)
                .order_by(AntiAbuseEvent.created_at.asc())
                .limit(batch_size)
            )
        )
        if not expired_ids:
            break
        result = db.execute(delete(AntiAbuseEvent).where(AntiAbuseEvent.id.in_(expired_ids)))
        db.commit()
        total_removed += result.rowcount or 0
        if len(expired_ids) < batch_size:
            break
    return total_removed
