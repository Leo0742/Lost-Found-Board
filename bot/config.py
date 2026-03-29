from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    api_base_url: str = "http://backend:8000/api"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
