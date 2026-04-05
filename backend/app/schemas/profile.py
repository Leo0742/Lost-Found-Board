from datetime import datetime

from pydantic import BaseModel, Field


class ContactMethodRead(BaseModel):
    id: str
    name: str
    value: str


class ContactMethodUpdate(BaseModel):
    id: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=40)
    value: str = Field(min_length=1, max_length=255)


class ProfileRead(BaseModel):
    telegram_user_id: int
    telegram_username: str | None = None
    telegram_display_name: str | None = None
    display_name: str | None = None
    preferred_contact_method: str | None = None
    preferred_contact_details: str | None = None
    pickup_location: str | None = None
    avatar_url: str | None = None
    telegram_avatar_url: str | None = None
    contact_methods: list[ContactMethodRead] = Field(default_factory=list)
    exposed_contact_methods: list[ContactMethodRead] = Field(default_factory=list)
    contact_visibility: str = "all"
    contact_visibility_method_id: str | None = None
    updated_at: datetime | None = None


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    preferred_contact_method: str | None = Field(default=None, max_length=32)
    preferred_contact_details: str | None = Field(default=None, max_length=255)
    pickup_location: str | None = Field(default=None, max_length=160)
    avatar_url: str | None = Field(default=None, max_length=500)
    contact_methods: list[ContactMethodUpdate] | None = None
    contact_visibility: str | None = Field(default=None, pattern="^(all|one)$")
    contact_visibility_method_id: str | None = Field(default=None, max_length=64)


class TelegramProfileSync(BaseModel):
    telegram_user_id: int
    telegram_username: str | None = Field(default=None, max_length=80)
    telegram_display_name: str | None = Field(default=None, max_length=120)
    telegram_avatar_url: str | None = Field(default=None, max_length=500)
