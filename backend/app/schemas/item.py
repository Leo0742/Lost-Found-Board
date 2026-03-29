from datetime import datetime

from pydantic import BaseModel, Field

from app.models.item import ItemStatus


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


class ItemRead(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

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
