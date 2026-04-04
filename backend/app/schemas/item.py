from datetime import datetime

from pydantic import BaseModel, Field

from app.models.item import ItemLifecycle, ItemStatus, ModerationStatus
from app.models.claim import ClaimStatus


class ItemBase(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    category: str = Field(default="Other", min_length=2, max_length=60)
    location: str = Field(min_length=2, max_length=120)
    status: ItemStatus
    contact_name: str = Field(min_length=2, max_length=80)
    telegram_username: str | None = Field(default=None, max_length=80)
    telegram_user_id: int | None = None
    owner_telegram_user_id: int | None = None
    owner_telegram_username: str | None = Field(default=None, max_length=80)
    owner_display_name: str | None = Field(default=None, max_length=120)
    image_path: str | None = Field(default=None, max_length=255)
    image_filename: str | None = Field(default=None, max_length=255)
    image_mime_type: str | None = Field(default=None, max_length=120)


class ItemCreate(ItemBase):
    pass


class ItemOwnerUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, min_length=5, max_length=2000)
    category: str | None = Field(default=None, min_length=2, max_length=60)
    location: str | None = Field(default=None, min_length=2, max_length=120)
    contact_name: str | None = Field(default=None, min_length=2, max_length=80)
    telegram_username: str | None = Field(default=None, max_length=80)


class ItemAdminUpdate(ItemOwnerUpdate):
    status: ItemStatus | None = None
    lifecycle: ItemLifecycle | None = None
    moderation_status: ModerationStatus | None = None
    moderation_reason: str | None = Field(default=None, max_length=255)
    is_verified: bool | None = None


class ItemPublicRead(BaseModel):
    id: int
    title: str
    description: str
    category: str
    location: str
    status: ItemStatus
    lifecycle: ItemLifecycle
    moderation_status: ModerationStatus
    moderation_reason: str | None = None
    is_verified: bool = False
    image_path: str | None = None
    image_filename: str | None = None
    image_mime_type: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class ItemRead(ItemPublicRead):
    moderated_at: datetime | None = None
    moderated_by: str | None = None
    verified_at: datetime | None = None
    contact_name: str
    telegram_username: str | None = None
    telegram_user_id: int | None = None
    owner_telegram_user_id: int | None = None
    owner_telegram_username: str | None = None
    owner_display_name: str | None = None


class MatchResult(BaseModel):
    id: int
    title: str
    status: ItemStatus
    category: str
    location: str
    relevance_score: float
    confidence: str
    reasons: list[str] = Field(default_factory=list)
    image_path: str | None = None


class InternalMatchResult(MatchResult):
    telegram_user_id: int | None = None


class SmartSearchResultRead(BaseModel):
    item: ItemPublicRead
    relevance_score: float
    reasons: list[str] = Field(default_factory=list)


class CategorySuggestionRead(BaseModel):
    category: str
    confidence: float
    reasons: list[str] = Field(default_factory=list)


class ItemOwnerAction(BaseModel):
    telegram_user_id: int | None = None


class ImageUploadResult(BaseModel):
    image_path: str
    image_filename: str
    image_mime_type: str
    image_url: str


class ItemModerationAction(BaseModel):
    action: str = Field(pattern="^(approve|reject|flag|unflag)$")
    reason: str | None = Field(default=None, max_length=255)


class ItemVerificationAction(BaseModel):
    is_verified: bool = True


class ItemLifecycleAdminAction(BaseModel):
    action: str = Field(pattern="^(resolve|reopen|delete)$")


class ItemBulkModerationAction(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=200)
    action: str = Field(pattern="^(approve|reject|flag|unflag)$")
    reason: str | None = Field(default=None, max_length=255)


class ItemBulkVerificationAction(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=200)
    is_verified: bool = True


class ItemBulkLifecycleAction(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=200)
    action: str = Field(pattern="^(resolve|reopen|delete)$")


class ItemBulkActionResult(BaseModel):
    item_id: int
    success: bool
    detail: str | None = None


class ItemBulkActionResponse(BaseModel):
    action: str
    processed: int
    succeeded: int
    failed: int
    results: list[ItemBulkActionResult] = Field(default_factory=list)


class ItemFlagRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=255)


class ClaimCreate(BaseModel):
    source_item_id: int
    target_item_id: int
    requester_name: str | None = Field(default=None, max_length=120)
    claim_message: str | None = Field(default=None, max_length=1000)


class InternalClaimCreate(ClaimCreate):
    requester_telegram_user_id: int


class ClaimRead(BaseModel):
    id: int
    source_item_id: int
    target_item_id: int
    requester_telegram_user_id: int | None = None
    owner_telegram_user_id: int | None = None
    requester_name: str | None = None
    claim_message: str | None = None
    status: ClaimStatus
    handoff_note: str | None = None
    resolved_by_claim: bool = False
    created_at: datetime
    updated_at: datetime
    source_item_title: str | None = None
    target_item_title: str | None = None
    shared_source_contact: str | None = None
    shared_target_contact: str | None = None


class ClaimAction(BaseModel):
    note: str | None = Field(default=None, max_length=255)


class InternalClaimAction(ClaimAction):
    telegram_user_id: int


class AuditEventRead(BaseModel):
    id: int
    event_type: str
    label: str | None = None
    summary: str | None = None
    actor_telegram_user_id: int | None = None
    item_id: int | None = None
    claim_id: int | None = None
    details: dict = Field(default_factory=dict)
    item_url: str | None = None
    claim_url: str | None = None
    created_at: datetime


class ModerationSignalRead(BaseModel):
    item_id: int
    total_flags: int = 0
    recent_flags_24h: int = 0
    recent_claims_24h: int = 0
    claim_count: int = 0
    duplicate_flags_24h: int = 0
    blocked_events_24h: int = 0
    last_flag_at: datetime | None = None
    suspicion_markers: list[str] = Field(default_factory=list)


class ModerationStatsRead(BaseModel):
    pending: int
    flagged: int
    active: int
    unresolved_claims: int
    recent_abuse_blocks_24h: int


class AdminQueueSummaryRead(BaseModel):
    pending_total: int
    flagged_total: int
    approved_total: int
    rejected_total: int
    high_risk_flagged_24h: int
    stale_pending_48h: int


class AdminObservabilityRead(BaseModel):
    recent_abuse_blocks_24h: int
    duplicate_flags_24h: int
    duplicate_claims_24h: int
    blocked_admin_audit_queries_24h: int
    claims_created_24h: int
    unresolved_claims_total: int
    cleanup: dict = Field(default_factory=dict)
    semantic_runtime: dict = Field(default_factory=dict)
