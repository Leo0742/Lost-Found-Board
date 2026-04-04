import logging

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
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount(settings.media_url_prefix, StaticFiles(directory=settings.media_root), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
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
