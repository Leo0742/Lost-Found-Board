from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib

from fastapi import HTTPException, Request
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.anti_abuse_event import AntiAbuseEvent


@dataclass(frozen=True)
class RateLimitRule:
    window_seconds: int
    max_hits: int
    error_message: str


def client_ip_hash(request: Request | None) -> str | None:
    if not request:
        return None
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    ip = forwarded or (request.client.host if request.client else "")
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:32]


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
