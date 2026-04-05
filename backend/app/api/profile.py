from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import get_authenticated_telegram_user_id, get_session_from_cookie, require_internal_access
from app.db.session import get_db
from app.models.auth_session import WebAuthSession
from app.models.user_profile import UserProfile
from app.schemas.profile import ProfileRead, ProfileUpdate, TelegramProfileSync

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _get_or_create_profile(db: Session, telegram_user_id: int) -> UserProfile:
    profile = db.scalar(select(UserProfile).where(UserProfile.telegram_user_id == telegram_user_id))
    if profile:
        return profile
    profile = UserProfile(telegram_user_id=telegram_user_id)
    db.add(profile)
    db.flush()
    return profile


def _profile_read(profile: UserProfile) -> ProfileRead:
    return ProfileRead(
        telegram_user_id=profile.telegram_user_id,
        telegram_username=profile.telegram_username,
        telegram_display_name=profile.telegram_display_name,
        display_name=profile.display_name,
        preferred_contact_method=profile.preferred_contact_method,
        preferred_contact_details=profile.preferred_contact_details,
        pickup_location=profile.pickup_location,
        avatar_url=profile.avatar_url,
        telegram_avatar_url=profile.telegram_avatar_url,
        updated_at=profile.updated_at,
    )


@router.get("/me", response_model=ProfileRead)
def get_my_profile(
    db: Session = Depends(get_db),
    telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
) -> ProfileRead:
    if not telegram_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram account is not linked.")

    profile = _get_or_create_profile(db, telegram_user_id)
    if session:
        profile.telegram_username = session.telegram_username
        profile.telegram_display_name = session.telegram_display_name
        if not profile.display_name:
            profile.display_name = session.telegram_display_name or session.telegram_username
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return _profile_read(profile)


@router.put("/me", response_model=ProfileRead)
def update_my_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
) -> ProfileRead:
    if not telegram_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Telegram account is not linked.")

    profile = _get_or_create_profile(db, telegram_user_id)
    profile.telegram_username = session.telegram_username if session else profile.telegram_username
    profile.telegram_display_name = session.telegram_display_name if session else profile.telegram_display_name

    profile.display_name = _normalize(payload.display_name)
    profile.preferred_contact_method = _normalize(payload.preferred_contact_method)
    profile.preferred_contact_details = _normalize(payload.preferred_contact_details)
    profile.pickup_location = _normalize(payload.pickup_location)
    profile.avatar_url = _normalize(payload.avatar_url)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _profile_read(profile)


@router.get("/internal/{telegram_user_id}", response_model=ProfileRead)
def get_profile_internal(telegram_user_id: int, db: Session = Depends(get_db), _: None = Depends(require_internal_access)) -> ProfileRead:
    profile = _get_or_create_profile(db, telegram_user_id)
    db.commit()
    db.refresh(profile)
    return _profile_read(profile)


@router.post("/internal/sync-telegram", response_model=ProfileRead)
def sync_telegram_profile_internal(
    payload: TelegramProfileSync,
    db: Session = Depends(get_db),
    _: None = Depends(require_internal_access),
) -> ProfileRead:
    profile = _get_or_create_profile(db, payload.telegram_user_id)
    profile.telegram_username = _normalize(payload.telegram_username)
    profile.telegram_display_name = _normalize(payload.telegram_display_name)
    profile.telegram_avatar_url = _normalize(payload.telegram_avatar_url)
    if not profile.display_name:
        profile.display_name = profile.telegram_display_name or profile.telegram_username
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _profile_read(profile)
