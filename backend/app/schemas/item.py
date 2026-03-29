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


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, min_length=5, max_length=2000)
    category: str | None = Field(default=None, min_length=2, max_length=60)
    location: str | None = Field(default=None, min_length=2, max_length=120)
    status: ItemStatus | None = None
    contact_name: str | None = Field(default=None, min_length=2, max_length=80)
    telegram_username: str | None = Field(default=None, max_length=80)
    telegram_user_id: int | None = None
    lifecycle: ItemLifecycle | None = None


class ItemRead(ItemBase):
    id: int
    lifecycle: ItemLifecycle
    moderation_status: ModerationStatus
    moderation_reason: str | None = None
    moderated_at: datetime | None = None
    moderated_by: str | None = None
    is_verified: bool = False
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class MatchResult(BaseModel):
    id: int
    title: str
    status: ItemStatus
    category: str
    location: str
    relevance_score: float
    confidence: str
    reasons: list[str] = Field(default_factory=list)
    telegram_user_id: int | None = None
    image_path: str | None = None


class SmartSearchResultRead(BaseModel):
    item: ItemRead
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


class ItemFlagRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=255)


class ClaimCreate(BaseModel):
    source_item_id: int
    target_item_id: int
    requester_telegram_user_id: int | None = None
    requester_name: str | None = Field(default=None, max_length=120)
    claim_message: str | None = Field(default=None, max_length=1000)


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
    telegram_user_id: int | None = None
    note: str | None = Field(default=None, max_length=255)
