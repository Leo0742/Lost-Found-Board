from fastapi import APIRouter, Depends, HTTPException, Header, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth import (
    AdminRole,
    get_admin_role_for_session,
    get_authenticated_telegram_user_id,
    get_session_from_cookie,
    require_admin,
    require_admin_or_moderator,
    require_internal_access,
)
from app.models.auth_session import WebAuthSession
from app.db.session import get_db
from app.models.item import ItemLifecycle, ItemStatus, ModerationStatus
from app.schemas.item import (
    ClaimAction,
    ClaimCreate,
    ClaimRead,
    CategorySuggestionRead,
    ImageUploadResult,
    ItemCreate,
    ItemFlagRequest,
    ItemLifecycleAdminAction,
    ItemModerationAction,
    ItemOwnerAction,
    ItemPublicRead,
    ItemRead,
    ItemUpdate,
    ItemVerificationAction,
    InternalMatchResult,
    MatchResult,
    SmartSearchResultRead,
)
from app.services.item_service import ItemService
from app.models.claim import ClaimStatus

router = APIRouter(prefix="/api/items", tags=["items"])


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    if auth_telegram_user_id:
        payload.telegram_user_id = auth_telegram_user_id
        payload.owner_telegram_user_id = auth_telegram_user_id
        if not payload.owner_telegram_username:
            payload.owner_telegram_username = payload.telegram_username
        if not payload.owner_display_name:
            payload.owner_display_name = payload.contact_name
    return service.create_item(payload)


@router.post("/upload-image", response_model=ImageUploadResult)
def upload_item_image(
    image: UploadFile,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    db: Session = Depends(get_db),
) -> ImageUploadResult:
    if not auth_telegram_user_id:
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.internal_api_token or x_internal_token != settings.internal_api_token:
            raise HTTPException(status_code=401, detail="Connect Telegram first")
    service = ItemService(db)
    image_path, image_filename, image_mime_type = service.save_image(image)
    image_url = service.image_url(image_path) or ""
    return ImageUploadResult(
        image_path=image_path,
        image_filename=image_filename,
        image_mime_type=image_mime_type,
        image_url=image_url,
    )


@router.get("", response_model=list[ItemPublicRead])
def list_items(
    status: ItemStatus | None = Query(default=None),
    lifecycle: ItemLifecycle | None = Query(default=ItemLifecycle.ACTIVE),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[ItemPublicRead]:
    service = ItemService(db)
    return service.list_items(status=status, category=category, q=q, lifecycle=lifecycle)


@router.get("/admin/items", response_model=list[ItemRead])
def list_items_admin(
    status: ItemStatus | None = Query(default=None),
    lifecycle: ItemLifecycle | None = Query(default=None),
    moderation_status: ModerationStatus | None = Query(default=None),
    q: str | None = Query(default=None),
    _: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> list[ItemRead]:
    service = ItemService(db)
    return service.list_items(status=status, q=q, lifecycle=lifecycle, moderation_status=moderation_status)


@router.get("/search", response_model=list[ItemPublicRead])
def search_items(q: str = Query(min_length=1), db: Session = Depends(get_db)) -> list[ItemPublicRead]:
    service = ItemService(db)
    return service.list_items(q=q)


@router.get("/search-smart", response_model=list[SmartSearchResultRead])
def smart_search_items(
    q: str = Query(min_length=1),
    limit: int = Query(default=8, ge=1, le=12),
    db: Session = Depends(get_db),
) -> list[SmartSearchResultRead]:
    service = ItemService(db)
    return service.smart_search(query=q, limit=limit)


@router.get("/categories", response_model=list[str])
def get_categories(db: Session = Depends(get_db)) -> list[str]:
    service = ItemService(db)
    return service.list_categories()


@router.get("/category-suggest", response_model=CategorySuggestionRead)
def suggest_category(title: str = Query(min_length=1), db: Session = Depends(get_db)) -> CategorySuggestionRead:
    service = ItemService(db)
    return service.suggest_category(title)


@router.get("/me", response_model=list[ItemRead])
def list_my_items_from_session(
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> list[ItemRead]:
    if not auth_telegram_user_id:
        raise HTTPException(status_code=401, detail="Connect Telegram first")
    service = ItemService(db)
    return service.list_my_items(auth_telegram_user_id)


@router.get("/internal/mine/{telegram_user_id}", response_model=list[ItemRead])
def list_my_items_internal(
    telegram_user_id: int,
    _: None = Depends(require_internal_access),
    db: Session = Depends(get_db),
) -> list[ItemRead]:
    service = ItemService(db)
    return service.list_my_items(telegram_user_id)


@router.post("/claim-requests", response_model=ClaimRead)
def create_claim(
    payload: ClaimCreate,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    source = service.get_item(payload.source_item_id)
    target = service.get_item(payload.target_item_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target item not found")
    if source.lifecycle != ItemLifecycle.ACTIVE or target.lifecycle != ItemLifecycle.ACTIVE:
        raise HTTPException(status_code=400, detail="Only active items can be claimed")
    if source.moderation_status != ModerationStatus.APPROVED or target.moderation_status != ModerationStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Claim is allowed only for approved reports")
    if source.status == target.status:
        raise HTTPException(status_code=400, detail="Claim requires opposite lost/found reports")
    source_owner_id = source.owner_telegram_user_id or source.telegram_user_id
    actor_id = auth_telegram_user_id or payload.requester_telegram_user_id
    if actor_id and source_owner_id != actor_id:
        raise HTTPException(status_code=403, detail="Only source owner can create this claim")
    claim = service.create_claim(
        source,
        target,
        requester_telegram_user_id=actor_id or source_owner_id,
        requester_name=payload.requester_name,
        claim_message=payload.claim_message,
    )
    return service.claim_read(claim, viewer_telegram_user_id=actor_id or source_owner_id)


@router.get("/claim-requests", response_model=list[ClaimRead])
def list_claims(
    telegram_user_id: int | None = Query(default=None),
    direction: str = Query(default="all"),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> list[ClaimRead]:
    if direction not in {"all", "incoming", "outgoing"}:
        raise HTTPException(status_code=400, detail="direction must be one of: all, incoming, outgoing")
    actor_id = auth_telegram_user_id or telegram_user_id
    if not actor_id:
        raise HTTPException(status_code=401, detail="Telegram identity is required")
    service = ItemService(db)
    claims = service.list_claims(telegram_user_id=actor_id, direction=direction)
    return [service.claim_read(claim, viewer_telegram_user_id=actor_id) for claim in claims]


@router.get("/{item_id}", response_model=ItemPublicRead)
def get_item(
    item_id: int,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    db: Session = Depends(get_db),
) -> ItemPublicRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    is_public_visible = item.lifecycle == ItemLifecycle.ACTIVE and item.moderation_status == ModerationStatus.APPROVED
    is_admin_or_moderator = bool(get_admin_role_for_session(session))
    if not is_public_visible and not is_admin_or_moderator and not (auth_telegram_user_id and service.is_owner(item, auth_telegram_user_id)):
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=ItemRead)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.update_item(item, payload)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, _: AdminRole = Depends(require_admin), db: Session = Depends(get_db)) -> None:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    service.delete_item(item)


def _actor_telegram_id(payload: ItemOwnerAction, auth_telegram_user_id: int | None) -> int:
    actor_id = auth_telegram_user_id or payload.telegram_user_id
    if not actor_id:
        raise HTTPException(status_code=401, detail="Telegram identity is required")
    return actor_id


@router.post("/{item_id}/resolve", response_model=ItemRead)
def resolve_item(
    item_id: int,
    payload: ItemOwnerAction,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not service.is_owner(item, _actor_telegram_id(payload, auth_telegram_user_id)):
        raise HTTPException(status_code=403, detail="Only the owner can resolve this item")
    return service.mark_resolved(item)


@router.post("/{item_id}/reopen", response_model=ItemRead)
def reopen_item(
    item_id: int,
    payload: ItemOwnerAction,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not service.is_owner(item, _actor_telegram_id(payload, auth_telegram_user_id)):
        raise HTTPException(status_code=403, detail="Only the owner can reopen this item")
    return service.reopen(item)


@router.post("/{item_id}/delete", response_model=ItemRead)
def soft_delete_item(
    item_id: int,
    payload: ItemOwnerAction,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not service.is_owner(item, _actor_telegram_id(payload, auth_telegram_user_id)):
        raise HTTPException(status_code=403, detail="Only the owner can delete this item")
    return service.delete_item(item)


@router.post("/{item_id}/flag", response_model=ItemRead)
def flag_item(item_id: int, payload: ItemFlagRequest, db: Session = Depends(get_db)) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.flag_item(item, payload.reason)


@router.post("/admin/items/{item_id}/moderate", response_model=ItemRead)
def moderate_item(
    item_id: int,
    payload: ItemModerationAction,
    role: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.moderate_item(item, payload.action, moderator=role.value, reason=payload.reason)


@router.post("/admin/items/{item_id}/verify", response_model=ItemRead)
def verify_item(
    item_id: int,
    payload: ItemVerificationAction,
    _: AdminRole = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.verify_item(item, payload.is_verified)


@router.post("/admin/items/{item_id}/lifecycle", response_model=ItemRead)
def admin_lifecycle(
    item_id: int,
    payload: ItemLifecycleAdminAction,
    _: AdminRole = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.admin_lifecycle_action(item, payload.action)


@router.get("/matches/{item_id}", response_model=list[MatchResult])
def get_matches(item_id: int, db: Session = Depends(get_db)) -> list[MatchResult]:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.matches_for_item(item, include_telegram_user_id=False)


@router.get("/internal/matches/{item_id}", response_model=list[InternalMatchResult])
def get_internal_matches(
    item_id: int,
    _: None = Depends(require_internal_access),
    db: Session = Depends(get_db),
) -> list[InternalMatchResult]:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.matches_for_item(item, include_telegram_user_id=True)


@router.post("/claim-requests/{claim_id}/approve", response_model=ClaimRead)
def approve_claim(
    claim_id: int,
    payload: ClaimAction,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(telegram_user_id=payload.telegram_user_id), auth_telegram_user_id)
    if claim.owner_telegram_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only claim target owner can approve")
    updated = service.update_claim_status(claim, ClaimStatus.APPROVED, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)


@router.post("/claim-requests/{claim_id}/reject", response_model=ClaimRead)
def reject_claim(
    claim_id: int,
    payload: ClaimAction,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(telegram_user_id=payload.telegram_user_id), auth_telegram_user_id)
    if claim.owner_telegram_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only claim target owner can reject")
    updated = service.update_claim_status(claim, ClaimStatus.REJECTED, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)


@router.post("/claim-requests/{claim_id}/cancel", response_model=ClaimRead)
def cancel_claim(
    claim_id: int,
    payload: ClaimAction,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(telegram_user_id=payload.telegram_user_id), auth_telegram_user_id)
    if claim.requester_telegram_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only requester can cancel")
    updated = service.update_claim_status(claim, ClaimStatus.CANCELLED, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)


@router.post("/claim-requests/{claim_id}/complete", response_model=ClaimRead)
def complete_claim(
    claim_id: int,
    payload: ClaimAction,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(telegram_user_id=payload.telegram_user_id), auth_telegram_user_id)
    if actor_id not in {claim.requester_telegram_user_id, claim.owner_telegram_user_id}:
        raise HTTPException(status_code=403, detail="Only participants can complete")

    source = service.get_item(claim.source_item_id)
    target = service.get_item(claim.target_item_id)
    if source:
        service.mark_resolved(source)
    if target:
        service.mark_resolved(target)
    updated = service.update_claim_status(claim, ClaimStatus.COMPLETED, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)


@router.post("/claim-requests/{claim_id}/not-match", response_model=ClaimRead)
def not_match_claim(
    claim_id: int,
    payload: ClaimAction,
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(telegram_user_id=payload.telegram_user_id), auth_telegram_user_id)
    if actor_id not in {claim.requester_telegram_user_id, claim.owner_telegram_user_id}:
        raise HTTPException(status_code=403, detail="Only participants can mark not-match")
    updated = service.update_claim_status(claim, ClaimStatus.NOT_MATCH, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)
