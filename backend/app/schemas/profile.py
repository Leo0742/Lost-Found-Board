from datetime import datetime

from pydantic import BaseModel, Field


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
    updated_at: datetime | None = None


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    preferred_contact_method: str | None = Field(default=None, max_length=32)
    preferred_contact_details: str | None = Field(default=None, max_length=255)
    pickup_location: str | None = Field(default=None, max_length=160)
    avatar_url: str | None = Field(default=None, max_length=500)


class TelegramProfileSync(BaseModel):
    telegram_user_id: int
    telegram_username: str | None = Field(default=None, max_length=80)
    telegram_display_name: str | None = Field(default=None, max_length=120)
    telegram_avatar_url: str | None = Field(default=None, max_length=500)
