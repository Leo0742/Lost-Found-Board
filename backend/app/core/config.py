from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lost & Found Board API"
    app_env: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/lost_found"
    cors_origins: str = ""
    cors_allow_credentials: bool = True
    embedding_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    semantic_matching_enabled: bool = True
    semantic_strict_mode: bool = False
    embedding_warmup_on_startup: bool = True
    media_tmp_ttl_hours: int = 24
    media_cleanup_interval_minutes: int = 60
    media_root: str = "/app/media"
    media_url_prefix: str = "/media"
    media_max_bytes: int = 5 * 1024 * 1024
    admin_secret: str = "change-me-admin-secret"
    allow_admin_secret_fallback: bool = False
    admin_telegram_user_ids: str = ""
    admin_telegram_usernames: str = ""
    admin_username_bootstrap_enabled: bool = False
    create_rate_limit_window_minutes: int = 10
    create_rate_limit_max_items: int = 5
    web_session_ttl_days: int = 30
    web_link_code_ttl_minutes: int = 10
    web_session_cookie_secure: bool = False
    web_session_cookie_samesite: str = "lax"
    internal_api_token: str = "change-me-internal-token"
    strict_internal_token: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_telegram_user_id_set(self) -> set[int]:
        ids: set[int] = set()
        for part in self.admin_telegram_user_ids.split(","):
            value = part.strip()
            if not value:
                continue
            try:
                ids.add(int(value))
            except ValueError:
                continue
        return ids

    @property
    def admin_telegram_username_set(self) -> set[str]:
        usernames: set[str] = set()
        for part in self.admin_telegram_usernames.split(","):
            value = part.strip().lstrip("@").lower()
            if value:
                usernames.add(value)
        return usernames

    @property
    def cors_origin_list(self) -> list[str]:
        parsed = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if parsed:
            return parsed
        if self.app_env.lower() == "dev":
            return [
                "http://localhost",
                "http://localhost:5173",
                "http://127.0.0.1",
                "http://127.0.0.1:5173",
            ]
        return []

    @property
    def is_dev_env(self) -> bool:
        return self.app_env.lower() in {"dev", "development", "local", "test"}

    @property
    def has_secure_internal_token(self) -> bool:
        token = (self.internal_api_token or "").strip()
        if not token:
            return False
        return token != "change-me-internal-token"


@lru_cache
def get_settings() -> Settings:
    return Settings()
