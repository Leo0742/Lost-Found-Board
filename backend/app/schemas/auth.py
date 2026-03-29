from datetime import datetime

from pydantic import BaseModel, Field


class TelegramIdentity(BaseModel):
    telegram_user_id: int
    telegram_username: str | None = None
    display_name: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    expires_at: datetime


class LinkCodeResponse(BaseModel):
    code: str
    expires_at: datetime


class WhoAmIResponse(BaseModel):
    linked: bool
    identity: TelegramIdentity | None = None
    admin_access: bool = False
    role: str | None = None


class LinkConfirmRequest(BaseModel):
    code: str = Field(min_length=4, max_length=16)
    telegram_user_id: int
    telegram_username: str | None = None
    display_name: str | None = Field(default=None, max_length=120)


class TelegramAdminAccessResponse(BaseModel):
    admin_access: bool
    role: str | None = None
