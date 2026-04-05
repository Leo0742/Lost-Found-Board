from datetime import UTC, datetime, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import (
    AdminRole,
    get_admin_role_for_session,
    get_authenticated_telegram_user_id,
    get_session_from_cookie,
    require_admin,
    require_admin_or_moderator,
    require_csrf_for_session,
    require_internal_access,
)
from app.models.auth_session import WebAuthSession
from app.core.config import get_settings
from app.db.session import get_db
from app.models.anti_abuse_event import AntiAbuseEvent
from app.models.audit_event import AuditEvent
from app.models.claim import Claim, ClaimStatus
from app.models.item import Item, ItemLifecycle, ItemStatus, ModerationStatus
from app.schemas.item import (
    ClaimAction,
    ClaimCreate,
    ClaimRead,
    InternalClaimAction,
    InternalClaimCreate,
    AuditEventRead,
    AdminObservabilityRead,
    AdminQueueSummaryRead,
    CategorySuggestionRead,
    ImageUploadResult,
    ItemAdminUpdate,
    ItemBulkActionResponse,
    ItemBulkActionResult,
    ItemBulkLifecycleAction,
    ItemBulkModerationAction,
    ItemBulkVerificationAction,
    ItemCreate,
    ItemFlagRequest,
    ItemLifecycleAdminAction,
    ItemModerationAction,
    ItemOwnerAction,
    ItemOwnerUpdate,
    ItemPublicRead,
    ItemRead,
    ItemVerificationAction,
    InternalLiveLocationShareRequest,
    InternalMatchResult,
    LiveLocationShareRequest,
    MatchResult,
    ModerationSignalRead,
    ModerationStatsRead,
    SmartSearchResultRead,
)
from app.services.anti_abuse import AbuseAction, RateLimitRule, client_ip_hash, enforce_rate_limit
from app.services.audit import describe_event, list_events
from app.services.item_service import ItemService
from app.services.maintenance_status import maintenance_status_store
from app.services.matching import semantic_runtime_status

router = APIRouter(prefix="/api/items", tags=["items"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    request: Request = None,
    db: Session = Depends(get_db),
) -> ItemRead:
    settings = get_settings()
    enforce_rate_limit(
        db,
        action=AbuseAction.CREATE_ITEM.value if auth_telegram_user_id else AbuseAction.CREATE_ITEM_ANON.value,
        rule=RateLimitRule(
            window_seconds=settings.create_rate_limit_window_minutes * 60,
            max_hits=settings.create_rate_limit_max_items if auth_telegram_user_id else settings.create_rate_limit_max_items_anon,
            error_message="Too many new reports in a short period. Please try again later.",
        ),
        actor_telegram_user_id=auth_telegram_user_id,
        session_id=session.id if session else None,
        ip_hash=client_ip_hash(request),
    )
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
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    request: Request = None,
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
    db: Session = Depends(get_db),
) -> ImageUploadResult:
    if not auth_telegram_user_id:
        settings = get_settings()
        if not settings.internal_api_token or x_internal_token != settings.internal_api_token:
            raise HTTPException(status_code=401, detail="Connect Telegram first")
    else:
        settings = get_settings()
        enforce_rate_limit(
            db,
            action=AbuseAction.UPLOAD_IMAGE.value,
            rule=RateLimitRule(
                window_seconds=settings.upload_rate_limit_window_minutes * 60,
                max_hits=settings.upload_rate_limit_max,
                error_message="Too many image uploads. Please wait before uploading more files.",
            ),
            actor_telegram_user_id=auth_telegram_user_id,
            session_id=session.id if session else None,
            ip_hash=client_ip_hash(request),
        )
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
    category: str | None = Query(default=None),
    is_verified: bool | None = Query(default=None),
    actor_telegram_user_id: int | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    sort_by: str = Query(default="created_at", pattern="^(created_at|updated_at|moderated_at|id)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=2000),
    suspicious_only: bool = Query(default=False),
    q: str | None = Query(default=None),
    _: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> list[ItemRead]:
    service = ItemService(db)
    return service.list_items_admin(
        status=status,
        q=q,
        lifecycle=lifecycle,
        moderation_status=moderation_status,
        category=category,
        is_verified=is_verified,
        actor_telegram_user_id=actor_telegram_user_id,
        created_from=created_from,
        created_to=created_to,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
        suspicious_only=suspicious_only,
    )


@router.get("/admin/audit-events", response_model=list[AuditEventRead])
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=5000),
    event_type: str | None = Query(default=None),
    actor_telegram_user_id: int | None = Query(default=None),
    item_id: int | None = Query(default=None),
    claim_id: int | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    _: AdminRole = Depends(require_admin_or_moderator),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    request: Request = None,
    db: Session = Depends(get_db),
) -> list[AuditEventRead]:
    settings = get_settings()
    enforce_rate_limit(
        db,
        action=AbuseAction.ADMIN_AUDIT_LIST.value,
        rule=RateLimitRule(
            window_seconds=settings.admin_audit_rate_limit_window_minutes * 60,
            max_hits=settings.admin_audit_rate_limit_max,
            error_message="Audit history is being queried too frequently. Please retry shortly.",
        ),
        actor_telegram_user_id=session.telegram_user_id if session else None,
        session_id=session.id if session else None,
        ip_hash=client_ip_hash(request),
    )
    events = list_events(
        db,
        limit=limit,
        offset=offset,
        event_type=event_type,
        actor_telegram_user_id=actor_telegram_user_id,
        item_id=item_id,
        claim_id=claim_id,
        created_from=created_from,
        created_to=created_to,
    )
    rows: list[AuditEventRead] = []
    for event in events:
        enriched = describe_event(event)
        rows.append(
            AuditEventRead(
                id=event.id,
                event_type=event.event_type,
                actor_telegram_user_id=event.actor_telegram_user_id,
                item_id=event.item_id,
                claim_id=event.claim_id,
                details=event.details or {},
                created_at=event.created_at,
                label=enriched["label"],
                summary=enriched["summary"],
                item_url=enriched["item_url"],
                claim_url=enriched["claim_url"],
            )
        )
    return rows


@router.get("/admin/moderation-signals", response_model=list[ModerationSignalRead])
def moderation_signals(
    item_ids: list[int] = Query(default=[]),
    _: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> list[ModerationSignalRead]:
    if not item_ids:
        return []
    now = datetime.now(UTC)
    since_24h = now - timedelta(hours=24)
    requested_ids = item_ids[:200]
    total_flags = {
        row[0]: row[1]
        for row in db.execute(
            select(AuditEvent.item_id, func.count(AuditEvent.id))
            .where(AuditEvent.event_type == "item_flagged", AuditEvent.item_id.in_(requested_ids))
            .group_by(AuditEvent.item_id)
        )
    }
    recent_flags = {
        row[0]: row[1]
        for row in db.execute(
            select(AuditEvent.item_id, func.count(AuditEvent.id))
            .where(
                AuditEvent.event_type == "item_flagged",
                AuditEvent.item_id.in_(requested_ids),
                AuditEvent.created_at >= since_24h,
            )
            .group_by(AuditEvent.item_id)
        )
    }
    last_flag_at = {
        row[0]: row[1]
        for row in db.execute(
            select(AuditEvent.item_id, func.max(AuditEvent.created_at))
            .where(AuditEvent.event_type == "item_flagged", AuditEvent.item_id.in_(requested_ids))
            .group_by(AuditEvent.item_id)
        )
    }
    duplicate_flags_24h = {
        row[0]: row[1]
        for row in db.execute(
            select(AntiAbuseEvent.item_id, func.count(AntiAbuseEvent.id))
            .where(
                AntiAbuseEvent.action == AbuseAction.FLAG_DUPLICATE.value,
                AntiAbuseEvent.item_id.in_(requested_ids),
                AntiAbuseEvent.created_at >= since_24h,
            )
            .group_by(AntiAbuseEvent.item_id)
        )
    }
    blocked_events_24h = {
        row[0]: row[1]
        for row in db.execute(
            select(AntiAbuseEvent.item_id, func.count(AntiAbuseEvent.id))
            .where(
                AntiAbuseEvent.item_id.in_(requested_ids),
                AntiAbuseEvent.blocked.is_(True),
                AntiAbuseEvent.created_at >= since_24h,
            )
            .group_by(AntiAbuseEvent.item_id)
        )
    }
    source_claim_counts = {
        row[0]: row[1]
        for row in db.execute(select(Claim.source_item_id, func.count(Claim.id)).where(Claim.source_item_id.in_(requested_ids)).group_by(Claim.source_item_id))
    }
    target_claim_counts = {
        row[0]: row[1]
        for row in db.execute(select(Claim.target_item_id, func.count(Claim.id)).where(Claim.target_item_id.in_(requested_ids)).group_by(Claim.target_item_id))
    }
    source_recent_claims = {
        row[0]: row[1]
        for row in db.execute(
            select(Claim.source_item_id, func.count(Claim.id))
            .where(Claim.source_item_id.in_(requested_ids), Claim.created_at >= since_24h)
            .group_by(Claim.source_item_id)
        )
    }
    target_recent_claims = {
        row[0]: row[1]
        for row in db.execute(
            select(Claim.target_item_id, func.count(Claim.id))
            .where(Claim.target_item_id.in_(requested_ids), Claim.created_at >= since_24h)
            .group_by(Claim.target_item_id)
        )
    }
    rows: list[ModerationSignalRead] = []
    for item_id in requested_ids:
        flag_total = int(total_flags.get(item_id) or 0)
        recent_flag_total = int(recent_flags.get(item_id) or 0)
        dup_flags = int(duplicate_flags_24h.get(item_id) or 0)
        blocked_events = int(blocked_events_24h.get(item_id) or 0)
        claim_total = int(source_claim_counts.get(item_id) or 0) + int(target_claim_counts.get(item_id) or 0)
        recent_claim_total = int(source_recent_claims.get(item_id) or 0) + int(target_recent_claims.get(item_id) or 0)
        markers: list[str] = []
        if recent_flag_total >= 3:
            markers.append("flag_spike_24h")
        if flag_total >= 5:
            markers.append("high_total_flags")
        if recent_claim_total >= 3:
            markers.append("claim_spike_24h")
        if dup_flags >= 2:
            markers.append("duplicate_flag_pressure")
        if blocked_events >= 2:
            markers.append("abuse_blocks_24h")
        rows.append(
            ModerationSignalRead(
                item_id=item_id,
                total_flags=flag_total,
                recent_flags_24h=recent_flag_total,
                recent_claims_24h=recent_claim_total,
                claim_count=claim_total,
                duplicate_flags_24h=dup_flags,
                blocked_events_24h=blocked_events,
                last_flag_at=last_flag_at.get(item_id),
                suspicion_markers=markers,
            )
        )
    return rows


def _run_bulk_action(
    *,
    item_ids: list[int],
    action: str,
    db: Session,
    runner,
) -> ItemBulkActionResponse:
    unique_ids = list(dict.fromkeys(item_ids))
    results: list[ItemBulkActionResult] = []
    for item_id in unique_ids:
        item = db.get(Item, item_id)
        if not item:
            results.append(ItemBulkActionResult(item_id=item_id, success=False, detail="Item not found"))
            continue
        try:
            runner(item)
            results.append(ItemBulkActionResult(item_id=item_id, success=True))
        except HTTPException as exc:
            results.append(ItemBulkActionResult(item_id=item_id, success=False, detail=str(exc.detail)))
            db.rollback()
        except Exception:
            db.rollback()
            logger.exception("Unexpected bulk action error for item_id=%s action=%s", item_id, action)
            results.append(ItemBulkActionResult(item_id=item_id, success=False, detail="Unexpected server error"))
    succeeded = sum(1 for row in results if row.success)
    return ItemBulkActionResponse(
        action=action,
        processed=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=results,
    )


@router.get("/admin/moderation-stats", response_model=ModerationStatsRead)
def moderation_stats(
    _: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> ModerationStatsRead:
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    return ModerationStatsRead(
        pending=db.scalar(select(func.count(Item.id)).where(Item.moderation_status == ModerationStatus.PENDING)) or 0,
        flagged=db.scalar(select(func.count(Item.id)).where(Item.moderation_status == ModerationStatus.FLAGGED)) or 0,
        active=db.scalar(select(func.count(Item.id)).where(Item.lifecycle == ItemLifecycle.ACTIVE)) or 0,
        unresolved_claims=db.scalar(select(func.count(Claim.id)).where(Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED]))) or 0,
        recent_abuse_blocks_24h=db.scalar(select(func.count(AntiAbuseEvent.id)).where(AntiAbuseEvent.blocked.is_(True), AntiAbuseEvent.created_at >= since_24h)) or 0,
    )


@router.get("/search", response_model=list[ItemPublicRead])
def search_items(q: str = Query(min_length=1), db: Session = Depends(get_db)) -> list[ItemPublicRead]:
    service = ItemService(db)
    return service.list_items(q=q)


@router.get("/search-smart", response_model=list[SmartSearchResultRead])
def smart_search_items(
    q: str = Query(min_length=1),
    limit: int = Query(default=8, ge=1, le=12),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    request: Request = None,
    db: Session = Depends(get_db),
) -> list[SmartSearchResultRead]:
    settings = get_settings()
    enforce_rate_limit(
        db,
        action=AbuseAction.SMART_SEARCH.value,
        rule=RateLimitRule(
            window_seconds=settings.smart_search_rate_limit_window_minutes * 60,
            max_hits=settings.smart_search_rate_limit_max,
            error_message="Search rate limit reached. Please wait before running more smart searches.",
        ),
        actor_telegram_user_id=auth_telegram_user_id,
        session_id=session.id if session else None,
        ip_hash=client_ip_hash(request),
    )
    service = ItemService(db)
    return service.smart_search(query=q, limit=limit)


@router.get("/categories", response_model=list[str])
def get_categories(db: Session = Depends(get_db)) -> list[str]:
    service = ItemService(db)
    return service.list_categories()


@router.get("/category-suggest", response_model=CategorySuggestionRead)
def suggest_category(
    title: str = Query(min_length=1),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    request: Request = None,
    db: Session = Depends(get_db),
) -> CategorySuggestionRead:
    settings = get_settings()
    enforce_rate_limit(
        db,
        action=AbuseAction.CATEGORY_SUGGEST.value,
        rule=RateLimitRule(
            window_seconds=settings.category_suggest_rate_limit_window_minutes * 60,
            max_hits=settings.category_suggest_rate_limit_max,
            error_message="Category suggestions are temporarily rate limited. Please try again in a moment.",
        ),
        actor_telegram_user_id=auth_telegram_user_id,
        session_id=session.id if session else None,
        ip_hash=client_ip_hash(request),
    )
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
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    request: Request = None,
    db: Session = Depends(get_db),
) -> ClaimRead:
    settings = get_settings()
    enforce_rate_limit(
        db,
        action=AbuseAction.CREATE_CLAIM.value,
        rule=RateLimitRule(
            window_seconds=settings.claim_rate_limit_window_minutes * 60,
            max_hits=settings.claim_rate_limit_max if auth_telegram_user_id else settings.claim_rate_limit_max_anon,
            error_message="Too many claim attempts. Please wait and try again later.",
        ),
        actor_telegram_user_id=auth_telegram_user_id,
        session_id=session.id if session else None,
        ip_hash=client_ip_hash(request),
        fingerprint=f"{payload.source_item_id}:{payload.target_item_id}",
    )
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
    if not auth_telegram_user_id:
        raise HTTPException(status_code=401, detail="Connect Telegram first")
    actor_id = auth_telegram_user_id
    if source_owner_id != actor_id:
        raise HTTPException(status_code=403, detail="Only source owner can create this claim")
    claim = service.create_claim(
        source,
        target,
        requester_telegram_user_id=actor_id or source_owner_id,
        requester_name=payload.requester_name,
        claim_message=payload.claim_message,
        session_id=session.id if session else None,
        ip_hash=client_ip_hash(request),
    )
    return service.claim_read(claim, viewer_telegram_user_id=actor_id or source_owner_id)


@router.get("/claim-requests", response_model=list[ClaimRead])
def list_claims(
    direction: str = Query(default="all"),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> list[ClaimRead]:
    if direction not in {"all", "incoming", "outgoing"}:
        raise HTTPException(status_code=400, detail="direction must be one of: all, incoming, outgoing")
    actor_id = auth_telegram_user_id
    if not actor_id:
        raise HTTPException(status_code=401, detail="Connect Telegram first")
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
def update_item(
    item_id: int,
    payload: ItemOwnerUpdate,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return item
    if auth_telegram_user_id and service.is_owner(item, auth_telegram_user_id):
        return service.update_item(item, update_data, actor_telegram_user_id=auth_telegram_user_id)
    role = get_admin_role_for_session(session)
    if role:
        raise HTTPException(status_code=403, detail="Use admin item patch endpoint")
    raise HTTPException(status_code=403, detail="Only owner can update this item")


@router.patch("/admin/items/{item_id}", response_model=ItemRead)
def admin_patch_item(
    item_id: int,
    payload: ItemAdminUpdate,
    _: None = Depends(require_csrf_for_session),
    role: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return item
    if role == AdminRole.MODERATOR:
        forbidden = {"lifecycle", "is_verified"}
        attempted = forbidden.intersection(update_data.keys())
        if attempted:
            raise HTTPException(status_code=403, detail=f"Moderator cannot patch fields: {', '.join(sorted(attempted))}")
    return service.update_item(item, update_data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    _: None = Depends(require_csrf_for_session),
    __: AdminRole = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    service.delete_item(item)


def _actor_telegram_id(payload: ItemOwnerAction, auth_telegram_user_id: int | None) -> int:
    if not auth_telegram_user_id:
        raise HTTPException(status_code=401, detail="Connect Telegram first")
    return auth_telegram_user_id


@router.post("/{item_id}/resolve", response_model=ItemRead)
def resolve_item(
    item_id: int,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not service.is_owner(item, _actor_telegram_id(ItemOwnerAction(), auth_telegram_user_id)):
        raise HTTPException(status_code=403, detail="Only the owner can resolve this item")
    return service.mark_resolved(item)


@router.post("/{item_id}/reopen", response_model=ItemRead)
def reopen_item(
    item_id: int,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not service.is_owner(item, _actor_telegram_id(ItemOwnerAction(), auth_telegram_user_id)):
        raise HTTPException(status_code=403, detail="Only the owner can reopen this item")
    return service.reopen(item)


@router.post("/{item_id}/delete", response_model=ItemRead)
def soft_delete_item(
    item_id: int,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not service.is_owner(item, _actor_telegram_id(ItemOwnerAction(), auth_telegram_user_id)):
        raise HTTPException(status_code=403, detail="Only the owner can delete this item")
    return service.delete_item(item)


@router.post("/{item_id}/flag", response_model=ItemRead)
def flag_item(
    item_id: int,
    payload: ItemFlagRequest,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    session: WebAuthSession | None = Depends(get_session_from_cookie),
    request: Request = None,
    db: Session = Depends(get_db),
) -> ItemRead:
    settings = get_settings()
    enforce_rate_limit(
        db,
        action=AbuseAction.FLAG_ITEM.value,
        rule=RateLimitRule(
            window_seconds=settings.flag_rate_limit_window_minutes * 60,
            max_hits=settings.flag_rate_limit_max if auth_telegram_user_id else settings.flag_rate_limit_max_anon,
            error_message="Too many flag submissions. Please try again later.",
        ),
        actor_telegram_user_id=auth_telegram_user_id,
        session_id=session.id if session else None,
        ip_hash=client_ip_hash(request),
        item_id=item_id,
    )
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.flag_item(
        item,
        payload.reason,
        actor_telegram_user_id=auth_telegram_user_id,
        session_id=session.id if session else None,
        ip_hash=client_ip_hash(request),
    )


@router.post("/admin/items/{item_id}/moderate", response_model=ItemRead)
def moderate_item(
    item_id: int,
    payload: ItemModerationAction,
    _: None = Depends(require_csrf_for_session),
    role: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.moderate_item(item, payload.action, moderator=role.value, reason=payload.reason)


@router.post("/admin/items/bulk-moderate", response_model=ItemBulkActionResponse)
def bulk_moderate_items(
    payload: ItemBulkModerationAction,
    _: None = Depends(require_csrf_for_session),
    role: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> ItemBulkActionResponse:
    service = ItemService(db)
    return _run_bulk_action(
        item_ids=payload.item_ids,
        action=payload.action,
        db=db,
        runner=lambda item: service.moderate_item(item, payload.action, moderator=role.value, reason=payload.reason),
    )


@router.post("/admin/items/{item_id}/verify", response_model=ItemRead)
def verify_item(
    item_id: int,
    payload: ItemVerificationAction,
    csrf_ok: None = Depends(require_csrf_for_session),
    role: AdminRole = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ItemRead:
    _ = (csrf_ok, role)
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.verify_item(item, payload.is_verified)


@router.post("/admin/items/bulk-verify", response_model=ItemBulkActionResponse)
def bulk_verify_items(
    payload: ItemBulkVerificationAction,
    _: None = Depends(require_csrf_for_session),
    _role: AdminRole = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ItemBulkActionResponse:
    service = ItemService(db)
    action = "verify" if payload.is_verified else "unverify"
    return _run_bulk_action(
        item_ids=payload.item_ids,
        action=action,
        db=db,
        runner=lambda item: service.verify_item(item, payload.is_verified),
    )


@router.post("/admin/items/{item_id}/lifecycle", response_model=ItemRead)
def admin_lifecycle(
    item_id: int,
    payload: ItemLifecycleAdminAction,
    csrf_ok: None = Depends(require_csrf_for_session),
    role: AdminRole = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ItemRead:
    _ = (csrf_ok, role)
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return service.admin_lifecycle_action(item, payload.action)


@router.post("/admin/items/bulk-lifecycle", response_model=ItemBulkActionResponse)
def bulk_lifecycle_items(
    payload: ItemBulkLifecycleAction,
    _: None = Depends(require_csrf_for_session),
    _role: AdminRole = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ItemBulkActionResponse:
    service = ItemService(db)
    return _run_bulk_action(
        item_ids=payload.item_ids,
        action=payload.action,
        db=db,
        runner=lambda item: service.admin_lifecycle_action(item, payload.action),
    )


@router.get("/admin/queue-summary", response_model=AdminQueueSummaryRead)
def admin_queue_summary(
    _: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> AdminQueueSummaryRead:
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    since_48h = datetime.now(UTC) - timedelta(hours=48)
    high_risk_rows = db.execute(
        select(AuditEvent.item_id)
        .where(
            AuditEvent.event_type == "item_flagged",
            AuditEvent.item_id.is_not(None),
            AuditEvent.created_at >= since_24h,
        )
        .group_by(AuditEvent.item_id)
        .having(func.count(AuditEvent.id) >= 3)
    )
    return AdminQueueSummaryRead(
        pending_total=db.scalar(select(func.count(Item.id)).where(Item.moderation_status == ModerationStatus.PENDING)) or 0,
        flagged_total=db.scalar(select(func.count(Item.id)).where(Item.moderation_status == ModerationStatus.FLAGGED)) or 0,
        approved_total=db.scalar(select(func.count(Item.id)).where(Item.moderation_status == ModerationStatus.APPROVED)) or 0,
        rejected_total=db.scalar(select(func.count(Item.id)).where(Item.moderation_status == ModerationStatus.REJECTED)) or 0,
        high_risk_flagged_24h=len(list(high_risk_rows)),
        stale_pending_48h=db.scalar(
            select(func.count(Item.id)).where(Item.moderation_status == ModerationStatus.PENDING, Item.created_at <= since_48h)
        )
        or 0,
    )


@router.get("/admin/observability", response_model=AdminObservabilityRead)
def admin_observability(
    _: AdminRole = Depends(require_admin_or_moderator),
    db: Session = Depends(get_db),
) -> AdminObservabilityRead:
    since_24h = datetime.now(UTC) - timedelta(hours=24)
    semantic = semantic_runtime_status()
    return AdminObservabilityRead(
        recent_abuse_blocks_24h=db.scalar(
            select(func.count(AntiAbuseEvent.id)).where(AntiAbuseEvent.blocked.is_(True), AntiAbuseEvent.created_at >= since_24h)
        )
        or 0,
        duplicate_flags_24h=db.scalar(
            select(func.count(AntiAbuseEvent.id)).where(
                AntiAbuseEvent.action == AbuseAction.FLAG_DUPLICATE.value,
                AntiAbuseEvent.created_at >= since_24h,
            )
        )
        or 0,
        duplicate_claims_24h=db.scalar(
            select(func.count(AntiAbuseEvent.id)).where(
                AntiAbuseEvent.action == AbuseAction.CLAIM_DUPLICATE.value,
                AntiAbuseEvent.created_at >= since_24h,
            )
        )
        or 0,
        blocked_admin_audit_queries_24h=db.scalar(
            select(func.count(AntiAbuseEvent.id)).where(
                AntiAbuseEvent.action == AbuseAction.ADMIN_AUDIT_LIST.value,
                AntiAbuseEvent.blocked.is_(True),
                AntiAbuseEvent.created_at >= since_24h,
            )
        )
        or 0,
        claims_created_24h=db.scalar(select(func.count(Claim.id)).where(Claim.created_at >= since_24h)) or 0,
        unresolved_claims_total=db.scalar(select(func.count(Claim.id)).where(Claim.status.in_([ClaimStatus.PENDING, ClaimStatus.APPROVED]))) or 0,
        cleanup={
            "anti_abuse_retention_days": get_settings().anti_abuse_event_retention_days,
            "audit_retention_days": get_settings().audit_event_retention_days,
            "media_temp_interval_minutes": get_settings().media_cleanup_interval_minutes,
            "media_orphan_interval_minutes": get_settings().media_orphan_cleanup_interval_minutes,
            "event_retention_interval_minutes": get_settings().event_retention_cleanup_interval_minutes,
            "maintenance_status": maintenance_status_store.snapshot(),
        },
        semantic_runtime={"state": semantic.state.value, "detail": semantic.detail},
    )


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
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(), auth_telegram_user_id)
    if claim.owner_telegram_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only claim target owner can approve")
    updated = service.update_claim_status(claim, ClaimStatus.APPROVED, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)


@router.post("/claim-requests/{claim_id}/reject", response_model=ClaimRead)
def reject_claim(
    claim_id: int,
    payload: ClaimAction,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(), auth_telegram_user_id)
    if claim.owner_telegram_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only claim target owner can reject")
    updated = service.update_claim_status(claim, ClaimStatus.REJECTED, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)


@router.post("/claim-requests/{claim_id}/cancel", response_model=ClaimRead)
def cancel_claim(
    claim_id: int,
    payload: ClaimAction,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(), auth_telegram_user_id)
    if claim.requester_telegram_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only requester can cancel")
    updated = service.update_claim_status(claim, ClaimStatus.CANCELLED, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)


@router.post("/claim-requests/{claim_id}/complete", response_model=ClaimRead)
def complete_claim(
    claim_id: int,
    payload: ClaimAction,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(), auth_telegram_user_id)
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
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = _actor_telegram_id(ItemOwnerAction(), auth_telegram_user_id)
    if actor_id not in {claim.requester_telegram_user_id, claim.owner_telegram_user_id}:
        raise HTTPException(status_code=403, detail="Only participants can mark not-match")
    updated = service.update_claim_status(claim, ClaimStatus.NOT_MATCH, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)


@router.post("/internal/{item_id}/resolve", response_model=ItemRead)
def internal_resolve_item(
    item_id: int,
    payload: ItemOwnerAction,
    _: None = Depends(require_internal_access),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    actor_id = payload.telegram_user_id
    if not actor_id or not service.is_owner(item, actor_id):
        raise HTTPException(status_code=403, detail="Only owner can resolve this item")
    return service.mark_resolved(item)


@router.post("/internal/{item_id}/reopen", response_model=ItemRead)
def internal_reopen_item(
    item_id: int,
    payload: ItemOwnerAction,
    _: None = Depends(require_internal_access),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    actor_id = payload.telegram_user_id
    if not actor_id or not service.is_owner(item, actor_id):
        raise HTTPException(status_code=403, detail="Only owner can reopen this item")
    return service.reopen(item)


@router.post("/internal/{item_id}/delete", response_model=ItemRead)
def internal_soft_delete_item(
    item_id: int,
    payload: ItemOwnerAction,
    _: None = Depends(require_internal_access),
    db: Session = Depends(get_db),
) -> ItemRead:
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    actor_id = payload.telegram_user_id
    if not actor_id or not service.is_owner(item, actor_id):
        raise HTTPException(status_code=403, detail="Only owner can delete this item")
    return service.delete_item(item)




@router.post("/claim-requests/{claim_id}/share-live-location", response_model=ClaimRead)
def share_live_location(
    claim_id: int,
    payload: LiveLocationShareRequest,
    _: None = Depends(require_csrf_for_session),
    auth_telegram_user_id: int | None = Depends(get_authenticated_telegram_user_id),
    db: Session = Depends(get_db),
) -> ClaimRead:
    if not auth_telegram_user_id:
        raise HTTPException(status_code=401, detail="Connect Telegram first")
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    updated = service.share_claim_live_location(
        claim=claim,
        actor_telegram_user_id=auth_telegram_user_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address_text=payload.address_text,
        ttl_minutes=payload.ttl_minutes,
    )
    return service.claim_read(updated, viewer_telegram_user_id=auth_telegram_user_id)


@router.post("/internal/claim-requests", response_model=ClaimRead)
def create_claim_internal(
    payload: InternalClaimCreate,
    _: None = Depends(require_internal_access),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    source = service.get_item(payload.source_item_id)
    target = service.get_item(payload.target_item_id)
    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target item not found")
    source_owner_id = source.owner_telegram_user_id or source.telegram_user_id
    if source_owner_id != payload.requester_telegram_user_id:
        raise HTTPException(status_code=403, detail="Only source owner can create this claim")
    claim = service.create_claim(
        source,
        target,
        requester_telegram_user_id=payload.requester_telegram_user_id,
        requester_name=payload.requester_name,
        claim_message=payload.claim_message,
    )
    return service.claim_read(claim, viewer_telegram_user_id=payload.requester_telegram_user_id)


@router.get("/internal/claim-requests", response_model=list[ClaimRead])
def list_claims_internal(
    telegram_user_id: int = Query(...),
    direction: str = Query(default="all"),
    _: None = Depends(require_internal_access),
    db: Session = Depends(get_db),
) -> list[ClaimRead]:
    service = ItemService(db)
    claims = service.list_claims(telegram_user_id=telegram_user_id, direction=direction)
    return [service.claim_read(claim, viewer_telegram_user_id=telegram_user_id) for claim in claims]


@router.post("/internal/claim-requests/{claim_id}/{action}", response_model=ClaimRead)
def claim_action_internal(
    claim_id: int,
    action: str,
    payload: InternalClaimAction,
    _: None = Depends(require_internal_access),
    db: Session = Depends(get_db),
) -> ClaimRead:
    transitions = {
        "approve": ClaimStatus.APPROVED,
        "reject": ClaimStatus.REJECTED,
        "cancel": ClaimStatus.CANCELLED,
        "complete": ClaimStatus.COMPLETED,
        "not-match": ClaimStatus.NOT_MATCH,
    }
    status_target = transitions.get(action)
    if not status_target:
        raise HTTPException(status_code=404, detail="Unsupported claim action")
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    actor_id = payload.telegram_user_id
    if action in {"approve", "reject"} and claim.owner_telegram_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only claim target owner can perform this action")
    if action == "cancel" and claim.requester_telegram_user_id != actor_id:
        raise HTTPException(status_code=403, detail="Only requester can cancel")
    if action in {"complete", "not-match"} and actor_id not in {claim.requester_telegram_user_id, claim.owner_telegram_user_id}:
        raise HTTPException(status_code=403, detail="Only participants can perform this action")
    if action == "complete":
        source = service.get_item(claim.source_item_id)
        target = service.get_item(claim.target_item_id)
        if source:
            service.mark_resolved(source)
        if target:
            service.mark_resolved(target)
    updated = service.update_claim_status(claim, status_target, note=payload.note)
    return service.claim_read(updated, viewer_telegram_user_id=actor_id)


@router.post("/internal/claim-requests/{claim_id}/share-live-location", response_model=ClaimRead)
def share_live_location_internal(
    claim_id: int,
    payload: InternalLiveLocationShareRequest,
    _: None = Depends(require_internal_access),
    db: Session = Depends(get_db),
) -> ClaimRead:
    service = ItemService(db)
    claim = service.get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    updated = service.share_claim_live_location(
        claim=claim,
        actor_telegram_user_id=payload.telegram_user_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        address_text=payload.address_text,
        ttl_minutes=payload.ttl_minutes,
    )
    return service.claim_read(updated, viewer_telegram_user_id=payload.telegram_user_id)
