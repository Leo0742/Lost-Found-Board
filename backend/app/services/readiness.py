from __future__ import annotations

from dataclasses import asdict, dataclass
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.services.matching import SemanticState, semantic_runtime_status
from app.services.media import media_storage_ready


@dataclass(slots=True)
class ReadinessReport:
    ready: bool
    database: bool
    services_initialized: bool
    matching_state: str
    matching_detail: str
    media_storage: bool
    config_ok: bool

    def as_dict(self) -> dict:
        return asdict(self)


def check_readiness(db: Session) -> ReadinessReport:
    settings = get_settings()
    db_ok = bool(db.execute(text("SELECT 1")).scalar())
    services_initialized = bool(settings.app_name and settings.media_root)
    matching = semantic_runtime_status()
    media_ok = media_storage_ready()
    internal_token_ok = settings.has_secure_internal_token or settings.is_dev_env or not settings.strict_internal_token
    config_ok = bool(settings.database_url and settings.media_url_prefix and internal_token_ok)

    fatal = [not db_ok, not services_initialized, not media_ok, not config_ok]
    if settings.semantic_strict_mode and matching.state != SemanticState.ENABLED:
        fatal.append(True)

    return ReadinessReport(
        ready=not any(fatal),
        database=db_ok,
        services_initialized=services_initialized,
        matching_state=matching.state.value,
        matching_detail=matching.detail,
        media_storage=media_ok,
        config_ok=config_ok,
    )
