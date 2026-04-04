from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import (
    create_web_session,
    ensure_session_csrf_token,
    generate_link_code,
    get_admin_role_for_identity,
    get_admin_role_for_session,
    get_session_from_cookie,
    rotate_web_session,
    require_csrf_for_session,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.auth_session import WebAuthSession
from app.schemas.auth import (
    LinkCodeResponse,
    CsrfTokenResponse,
    LinkConfirmRequest,
    SessionResponse,
    TelegramAdminAccessResponse,
    TelegramIdentity,
    WhoAmIResponse,
)
from app.services.audit import log_event
from app.services.anti_abuse import RateLimitRule, client_ip_hash, enforce_rate_limit

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
def whoami(
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    db: Session = Depends(get_db),
) -> WhoAmIResponse:
    if not session or not session.telegram_user_id:
        return WhoAmIResponse(linked=False, identity=None, admin_access=False, role=None)
    ensure_session_csrf_token(db, session)
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


@router.get("/csrf", response_model=CsrfTokenResponse)
def get_csrf_token(
    response: Response,
    db: Session = Depends(get_db),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
) -> CsrfTokenResponse:
    created = False
    if not session:
        session = create_web_session(db)
        created = True
    token = ensure_session_csrf_token(db, session)
    if created:
        _set_session_cookie(response, session.id)
    return CsrfTokenResponse(csrf_token=token)


@router.post("/link-code", response_model=LinkCodeResponse)
def create_link_code(
    response: Response,
    _: None = Depends(require_csrf_for_session),
    db: Session = Depends(get_db),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    request: Request = None,
) -> LinkCodeResponse:
    created = False
    if not session:
        session = create_web_session(db)
        created = True
    settings = get_settings()
    enforce_rate_limit(
        db,
        action="link_code_create",
        rule=RateLimitRule(
            window_seconds=settings.link_code_rate_limit_window_minutes * 60,
            max_hits=settings.link_code_rate_limit_max,
            error_message="Too many link code requests. Please wait before generating another code.",
        ),
        actor_telegram_user_id=session.telegram_user_id if session else None,
        session_id=session.id if session else None,
        ip_hash=client_ip_hash(request),
    )
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
def confirm_link(payload: LinkConfirmRequest, response: Response, request: Request, db: Session = Depends(get_db)) -> WhoAmIResponse:
    settings = get_settings()
    enforce_rate_limit(
        db,
        action="link_confirm_attempt",
        rule=RateLimitRule(
            window_seconds=settings.link_confirm_rate_limit_window_minutes * 60,
            max_hits=settings.link_confirm_rate_limit_max,
            error_message="Too many link confirmation attempts. Please wait and try again.",
        ),
        actor_telegram_user_id=payload.telegram_user_id,
        session_id=None,
        ip_hash=client_ip_hash(request),
        fingerprint=payload.code.upper(),
    )
    session = db.scalar(select(WebAuthSession).where(WebAuthSession.link_code == payload.code.upper()))
    if not session or not session.link_code_expires_at or _as_utc(session.link_code_expires_at) < _now():
        raise HTTPException(status_code=404, detail="Link code is invalid or expired")

    linked_session = rotate_web_session(
        db,
        session,
        telegram_user_id=payload.telegram_user_id,
        telegram_username=payload.telegram_username,
        telegram_display_name=payload.display_name,
    )
    _set_session_cookie(response, linked_session.id)
    log_event(
        db,
        "telegram_linked",
        actor_telegram_user_id=linked_session.telegram_user_id,
        details={"telegram_username": linked_session.telegram_username},
    )
    db.commit()
    role = get_admin_role_for_session(linked_session)
    return WhoAmIResponse(
        linked=True,
        identity=TelegramIdentity(
            telegram_user_id=linked_session.telegram_user_id,
            telegram_username=linked_session.telegram_username,
            display_name=linked_session.telegram_display_name,
        ),
        admin_access=bool(role),
        role=role.value if role else None,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    _: None = Depends(require_csrf_for_session),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    db: Session = Depends(get_db),
) -> None:
    if session:
        rotated = rotate_web_session(
            db,
            session,
            telegram_user_id=None,
            telegram_username=None,
            telegram_display_name=None,
        )
        _set_session_cookie(response, rotated.id)
        return
    response.delete_cookie("lfb_session")


@router.post("/unlink", status_code=status.HTTP_204_NO_CONTENT)
def unlink_telegram(
    response: Response,
    _: None = Depends(require_csrf_for_session),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    db: Session = Depends(get_db),
) -> None:
    if not session:
        return
    actor_id = session.telegram_user_id
    rotated = rotate_web_session(
        db,
        session,
        telegram_user_id=None,
        telegram_username=None,
        telegram_display_name=None,
    )
    _set_session_cookie(response, rotated.id)
    log_event(db, "telegram_unlinked", actor_telegram_user_id=actor_id)
    db.commit()


@router.get("/telegram-admin-access", response_model=TelegramAdminAccessResponse)
def telegram_admin_access(
    telegram_user_id: int = Query(...),
    telegram_username: str | None = Query(default=None),
) -> TelegramAdminAccessResponse:
    role = get_admin_role_for_identity(telegram_user_id=telegram_user_id, telegram_username=telegram_username)
    return TelegramAdminAccessResponse(admin_access=bool(role), role=role.value if role else None)
