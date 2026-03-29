from datetime import datetime

from pydantic import BaseModel, Field

from app.models.item import ItemLifecycle, ItemStatus


class ItemBase(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=2000)
    category: str = Field(default="Other", min_length=2, max_length=60)
    location: str = Field(min_length=2, max_length=120)
    status: ItemStatus
    contact_name: str = Field(min_length=2, max_length=80)
    telegram_username: str | None = Field(default=None, max_length=80)
    telegram_user_id: int | None = None


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


class ItemOwnerAction(BaseModel):
    telegram_user_id: int
