from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str | None = None
    api_base_url: str = "http://backend:8000/api"
    api_timeout_seconds: float = 15.0
    match_timeout_seconds: float = 45.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
