from datetime import UTC, datetime, timedelta
from secrets import token_hex

from fastapi import Cookie, Depends
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
