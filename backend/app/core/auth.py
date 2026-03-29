from datetime import UTC, datetime, timedelta
from enum import StrEnum
from secrets import token_hex

from fastapi import Cookie, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth_session import WebAuthSession


def _now() -> datetime:
    return datetime.now(UTC)


def generate_session_id() -> str:
    return token_hex(24)


def generate_link_code() -> str:
    return token_hex(3).upper()


def create_web_session(db: Session) -> WebAuthSession:
    settings = get_settings()
    session = WebAuthSession(
        id=generate_session_id(),
        expires_at=_now() + timedelta(days=settings.web_session_ttl_days),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_from_cookie(
    session_id: str | None = Cookie(default=None, alias="lfb_session"),
    db: Session = Depends(get_db),
) -> WebAuthSession | None:
    if not session_id:
        return None
    session = db.get(WebAuthSession, session_id)
    if not session:
        return None
    if session.expires_at <= _now():
        return None
    return session


def get_authenticated_telegram_user_id(session: WebAuthSession | None = Depends(get_session_from_cookie)) -> int | None:
    if not session or not session.telegram_user_id:
        return None
    return session.telegram_user_id


class AdminRole(StrEnum):
    ADMIN = "admin"
    MODERATOR = "moderator"


def _normalized_username(username: str | None) -> str | None:
    if not username:
        return None
    value = username.strip().lstrip("@").lower()
    return value or None


def get_admin_role_for_identity(telegram_user_id: int | None, telegram_username: str | None) -> AdminRole | None:
    settings = get_settings()
    if telegram_user_id and telegram_user_id in settings.admin_telegram_user_id_set:
        return AdminRole.ADMIN
    username = _normalized_username(telegram_username)
    if username and username in settings.admin_telegram_username_set:
        return AdminRole.MODERATOR
    return None


def get_admin_role_for_session(session: WebAuthSession | None) -> AdminRole | None:
    if not session:
        return None
    return get_admin_role_for_identity(session.telegram_user_id, session.telegram_username)


def require_admin_or_moderator(
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    x_admin_secret: str | None = Header(default=None),
) -> AdminRole:
    role = get_admin_role_for_session(session)
    if role:
        return role
    settings = get_settings()
    if settings.allow_admin_secret_fallback and x_admin_secret and x_admin_secret == settings.admin_secret:
        return AdminRole.ADMIN
    raise HTTPException(status_code=403, detail="Admin access denied")


def require_admin(
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    x_admin_secret: str | None = Header(default=None),
) -> AdminRole:
    role = get_admin_role_for_session(session)
    if role == AdminRole.ADMIN:
        return role
    settings = get_settings()
    if settings.allow_admin_secret_fallback and x_admin_secret and x_admin_secret == settings.admin_secret:
        return AdminRole.ADMIN
    raise HTTPException(status_code=403, detail="Admin access denied")
