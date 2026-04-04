import logging
import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from contextlib import asynccontextmanager, suppress

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
from app.services.media import cleanup_stale_temp_uploads, ensure_media_dirs, cleanup_finalized_orphans
from app.services.readiness import check_readiness
from app.services.anti_abuse import cleanup_expired_events
from app.services.audit import cleanup_expired_events as cleanup_expired_audit_events
from app.db.session import SessionLocal

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MaintenanceStep:
    name: str
    interval_seconds: int
    runner: Callable[[], int | None]
    success_log_template: str


def _run_maintenance_step(step: MaintenanceStep) -> None:
    try:
        removed = step.runner()
        if removed:
            logger.info(step.success_log_template, removed)
    except Exception:
        logger.exception("Maintenance step '%s' failed.", step.name)


@asynccontextmanager
async def lifespan(_: FastAPI):
    cleanup_task: asyncio.Task | None = None
    ensure_media_dirs()
    _run_maintenance_step(
        MaintenanceStep(
            name="startup_temp_media_cleanup",
            interval_seconds=0,
            runner=cleanup_stale_temp_uploads,
            success_log_template="Removed %s stale temporary media files on startup.",
        )
    )
    _run_maintenance_step(
        MaintenanceStep(
            name="startup_finalized_orphan_cleanup",
            interval_seconds=0,
            runner=cleanup_finalized_orphans,
            success_log_template="Removed %s orphaned finalized media files on startup.",
        )
    )

    try:
        with SessionLocal() as db:
            abuse_removed = cleanup_expired_events(db, retention_days=settings.anti_abuse_event_retention_days)
            audit_removed = cleanup_expired_audit_events(db, retention_days=settings.audit_event_retention_days)
        if abuse_removed:
            logger.info("Removed %s expired anti-abuse events on startup.", abuse_removed)
        if audit_removed:
            logger.info("Removed %s expired audit events on startup.", audit_removed)
    except Exception as exc:
        logger.info("Skipping event retention cleanup on startup: %s", exc)

    if settings.embedding_warmup_on_startup:
        warmup_embedding_model()
    else:
        logger.info("Semantic warmup skipped by configuration (EMBEDDING_WARMUP_ON_STARTUP=false).")

    semantic = semantic_runtime_status()
    logger.info("Semantic matching startup state: %s (%s)", semantic.state.value, semantic.detail)
    logger.info("Internal API token configured: %s", "yes" if settings.internal_api_token else "no")
    if settings.strict_internal_token and not settings.is_dev_env and not settings.has_secure_internal_token:
        raise RuntimeError("INTERNAL_API_TOKEN must be set to a non-default value outside dev/test environments.")

    async def _periodic_maintenance() -> None:
        steps: list[MaintenanceStep] = []
        temp_interval = settings.media_cleanup_interval_minutes * 60
        orphan_interval = settings.media_orphan_cleanup_interval_minutes * 60
        retention_interval = settings.event_retention_cleanup_interval_minutes * 60

        if temp_interval <= 0:
            logger.info("Periodic media temp cleanup disabled (MEDIA_CLEANUP_INTERVAL_MINUTES<=0).")
        else:
            steps.append(
                MaintenanceStep(
                    name="temp_media_cleanup",
                    interval_seconds=temp_interval,
                    runner=cleanup_stale_temp_uploads,
                    success_log_template="Periodic cleanup removed %s stale temp media files.",
                )
            )
        if orphan_interval <= 0:
            logger.info("Periodic finalized orphan cleanup disabled (MEDIA_ORPHAN_CLEANUP_INTERVAL_MINUTES<=0).")
        else:
            steps.append(
                MaintenanceStep(
                    name="finalized_orphan_cleanup",
                    interval_seconds=orphan_interval,
                    runner=cleanup_finalized_orphans,
                    success_log_template="Periodic cleanup removed %s orphaned finalized media files.",
                )
            )
        if retention_interval <= 0:
            logger.info("Periodic event retention cleanup disabled (EVENT_RETENTION_CLEANUP_INTERVAL_MINUTES<=0).")
        else:
            steps.extend(
                [
                    MaintenanceStep(
                        name="anti_abuse_retention_cleanup",
                        interval_seconds=retention_interval,
                        runner=lambda: _cleanup_anti_abuse_events(),
                        success_log_template="Periodic cleanup removed %s expired anti-abuse events.",
                    ),
                    MaintenanceStep(
                        name="audit_retention_cleanup",
                        interval_seconds=retention_interval,
                        runner=lambda: _cleanup_audit_events(),
                        success_log_template="Periodic cleanup removed %s expired audit events.",
                    ),
                ]
            )

        if not steps:
            logger.info("All periodic maintenance steps disabled by configuration.")
            return

        next_run = {step.name: asyncio.get_running_loop().time() + step.interval_seconds for step in steps}
        while True:
            try:
                now = asyncio.get_running_loop().time()
                sleep_for = max(1.0, min(next_run.values()) - now)
                await asyncio.sleep(sleep_for)
                now = asyncio.get_running_loop().time()
                for step in steps:
                    if now < next_run[step.name]:
                        continue
                    _run_maintenance_step(step)
                    next_run[step.name] = now + step.interval_seconds
            except asyncio.CancelledError:
                logger.info("Periodic maintenance task cancelled.")
                raise
            except Exception:
                logger.exception("Unexpected periodic maintenance loop failure; continuing.")
                await asyncio.sleep(2)

    def _cleanup_anti_abuse_events() -> int:
        with SessionLocal() as db:
            return cleanup_expired_events(db, retention_days=settings.anti_abuse_event_retention_days)

    def _cleanup_audit_events() -> int:
        with SessionLocal() as db:
            return cleanup_expired_audit_events(db, retention_days=settings.audit_event_retention_days)

    cleanup_task = asyncio.create_task(_periodic_maintenance())
    try:
        yield
    finally:
        if cleanup_task:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task


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
