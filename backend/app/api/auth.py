from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import create_web_session, generate_link_code, get_admin_role_for_identity, get_admin_role_for_session, get_session_from_cookie
from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth_session import WebAuthSession
from app.schemas.auth import (
    LinkCodeResponse,
    LinkConfirmRequest,
    SessionResponse,
    TelegramAdminAccessResponse,
    TelegramIdentity,
    WhoAmIResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _set_session_cookie(response: Response, session_id: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key="lfb_session",
        value=session_id,
        httponly=True,
        samesite=settings.web_session_cookie_samesite,
        secure=settings.web_session_cookie_secure,
        max_age=60 * 60 * 24 * settings.web_session_ttl_days,
    )


@router.post("/session", response_model=SessionResponse)
def create_session(response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    session = create_web_session(db)
    _set_session_cookie(response, session.id)
    return SessionResponse(session_id=session.id, expires_at=session.expires_at)


@router.get("/me", response_model=WhoAmIResponse)
def whoami(session: WebAuthSession | None = Depends(get_session_from_cookie)) -> WhoAmIResponse:
    if not session or not session.telegram_user_id:
        return WhoAmIResponse(linked=False, identity=None, admin_access=False, role=None)
    role = get_admin_role_for_session(session)
    return WhoAmIResponse(
        linked=True,
        identity=TelegramIdentity(
            telegram_user_id=session.telegram_user_id,
            telegram_username=session.telegram_username,
            display_name=session.telegram_display_name,
        ),
        admin_access=bool(role),
        role=role.value if role else None,
    )


@router.post("/link-code", response_model=LinkCodeResponse)
def create_link_code(
    response: Response,
    db: Session = Depends(get_db),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
) -> LinkCodeResponse:
    created = False
    if not session:
        session = create_web_session(db)
        created = True
    settings = get_settings()
    expires_at = _now() + timedelta(minutes=settings.web_link_code_ttl_minutes)
    code = generate_link_code()
    while db.scalar(select(WebAuthSession).where(WebAuthSession.link_code == code)):
        code = generate_link_code()

    session.link_code = code
    session.link_code_expires_at = expires_at
    db.add(session)
    db.commit()
    db.refresh(session)
    if created:
        _set_session_cookie(response, session.id)
    return LinkCodeResponse(code=code, expires_at=expires_at)


@router.post("/link/confirm", response_model=WhoAmIResponse)
def confirm_link(payload: LinkConfirmRequest, db: Session = Depends(get_db)) -> WhoAmIResponse:
    session = db.scalar(select(WebAuthSession).where(WebAuthSession.link_code == payload.code.upper()))
    if not session or not session.link_code_expires_at or _as_utc(session.link_code_expires_at) < _now():
        raise HTTPException(status_code=404, detail="Link code is invalid or expired")

    session.telegram_user_id = payload.telegram_user_id
    session.telegram_username = payload.telegram_username
    session.telegram_display_name = payload.display_name
    session.linked_at = _now()
    session.link_code = None
    session.link_code_expires_at = None
    db.add(session)
    db.commit()
    db.refresh(session)
    role = get_admin_role_for_session(session)
    return WhoAmIResponse(
        linked=True,
        identity=TelegramIdentity(
            telegram_user_id=session.telegram_user_id,
            telegram_username=session.telegram_username,
            display_name=session.telegram_display_name,
        ),
        admin_access=bool(role),
        role=role.value if role else None,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, session: WebAuthSession | None = Depends(get_session_from_cookie), db: Session = Depends(get_db)) -> None:
    if session:
        session.telegram_user_id = None
        session.telegram_username = None
        session.telegram_display_name = None
        session.linked_at = None
        db.add(session)
        db.commit()
    response.delete_cookie("lfb_session")


@router.post("/unlink", status_code=status.HTTP_204_NO_CONTENT)
def unlink_telegram(session: WebAuthSession | None = Depends(get_session_from_cookie), db: Session = Depends(get_db)) -> None:
    if not session:
        return
    session.telegram_user_id = None
    session.telegram_username = None
    session.telegram_display_name = None
    session.linked_at = None
    session.link_code = None
    session.link_code_expires_at = None
    db.add(session)
    db.commit()


@router.get("/telegram-admin-access", response_model=TelegramAdminAccessResponse)
def telegram_admin_access(
    telegram_user_id: int = Query(...),
    telegram_username: str | None = Query(default=None),
) -> TelegramAdminAccessResponse:
    role = get_admin_role_for_identity(telegram_user_id=telegram_user_id, telegram_username=telegram_username)
    return TelegramAdminAccessResponse(admin_access=bool(role), role=role.value if role else None)
