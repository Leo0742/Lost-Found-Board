from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

TMP_PREFIX = "tmp_"


def media_root() -> Path:
    return Path(get_settings().media_root)


def ensure_media_dirs() -> tuple[Path, Path]:
    root = media_root()
    tmp = root / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    return root, tmp


def is_tmp_path(path: str | None) -> bool:
    return bool(path and path.startswith("tmp/"))


def finalize_uploaded_image(path: str | None) -> str | None:
    if not is_tmp_path(path):
        return path
    root, _ = ensure_media_dirs()
    src = root / path
    if not src.exists():
        return None
    name = src.name
    if name.startswith(TMP_PREFIX):
        name = name[len(TMP_PREFIX):]
    dest = root / name
    src.replace(dest)
    return name


def remove_media_file(path: str | None) -> None:
    if not path:
        return
    root = media_root()
    target = root / path
    try:
        if target.exists() and target.is_file():
            target.unlink()
    except OSError as exc:
        logger.warning("Failed to remove media file '%s': %s", path, exc)


def cleanup_stale_temp_uploads(now: datetime | None = None) -> int:
    settings = get_settings()
    _, tmp_dir = ensure_media_dirs()
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(hours=settings.media_tmp_ttl_hours)
    removed = 0
    for file in tmp_dir.iterdir():
        if not file.is_file():
            continue
        modified = datetime.fromtimestamp(file.stat().st_mtime, tz=UTC)
        if modified < cutoff:
            try:
                file.unlink()
                removed += 1
            except OSError as exc:
                logger.warning("Failed to cleanup stale temp media '%s': %s", file.name, exc)
    return removed


def media_storage_ready() -> bool:
    try:
        root, tmp = ensure_media_dirs()
        probe = tmp / ".probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return root.exists() and tmp.exists()
    except OSError:
        return False
