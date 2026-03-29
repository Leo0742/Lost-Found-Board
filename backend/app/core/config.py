from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lost & Found Board API"
    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/lost_found"
    cors_origins: str = "*"
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_warmup_on_startup: bool = True
    media_root: str = "/app/media"
    media_url_prefix: str = "/media"
    media_max_bytes: int = 5 * 1024 * 1024
    admin_secret: str = "change-me-admin-secret"
    create_rate_limit_window_minutes: int = 10
    create_rate_limit_max_items: int = 5
    web_session_ttl_days: int = 30
    web_link_code_ttl_minutes: int = 10

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
