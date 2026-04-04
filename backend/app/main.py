import logging
import asyncio

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api.auth import router as auth_router
from app.api.items import router as items_router
from app.core.config import get_settings
from app.db.session import get_db
from app.services.matching import semantic_runtime_status, warmup_embedding_model
from app.services.media import cleanup_stale_temp_uploads, ensure_media_dirs
from app.services.readiness import check_readiness

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_task: asyncio.Task | None = None
    ensure_media_dirs()
    cleaned = cleanup_stale_temp_uploads()
    if cleaned:
        logger.info("Removed %s stale temporary media files on startup.", cleaned)

    if settings.embedding_warmup_on_startup:
        warmup_embedding_model()
    else:
        logger.info("Semantic warmup skipped by configuration (EMBEDDING_WARMUP_ON_STARTUP=false).")

    semantic = semantic_runtime_status()
    logger.info("Semantic matching startup state: %s (%s)", semantic.state.value, semantic.detail)
    logger.info("Internal API token configured: %s", "yes" if settings.internal_api_token else "no")

    async def _periodic_temp_cleanup() -> None:
        interval_minutes = settings.media_cleanup_interval_minutes
        if interval_minutes <= 0:
            logger.info("Periodic media temp cleanup disabled (MEDIA_CLEANUP_INTERVAL_MINUTES<=0).")
            return
        while True:
            await asyncio.sleep(interval_minutes * 60)
            removed = cleanup_stale_temp_uploads()
            if removed:
                logger.info("Periodic cleanup removed %s stale temp media files.", removed)

    cleanup_task = asyncio.create_task(_periodic_temp_cleanup())
    try:
        yield
    finally:
        if cleanup_task:
            cleanup_task.cancel()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount(settings.media_url_prefix, StaticFiles(directory=settings.media_root), name="media")

allow_origins = settings.cors_origin_list
allow_credentials = settings.cors_allow_credentials
if "*" in allow_origins and allow_credentials:
    logger.warning("CORS_ORIGINS includes '*' with credentials; disabling credentials for safety.")
    allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins or [],
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    report = check_readiness(db)
    if report.ready:
        return report.as_dict()
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=report.as_dict())


app.include_router(items_router)
app.include_router(auth_router)
