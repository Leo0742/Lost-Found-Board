from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any


@dataclass
class MaintenanceStepStatus:
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error: str | None = None
    last_removed_count: int = 0
    total_removed: int = 0
    runs: int = 0
    failures: int = 0

    def health(self, now: datetime) -> str:
        if self.last_success_at is None and self.last_error_at is None and self.last_attempt_at is None:
            return "stale"
        if self.last_error_at and (self.last_success_at is None or self.last_error_at >= self.last_success_at):
            if now - self.last_error_at <= timedelta(hours=6):
                return "warning"
        if self.last_success_at is None:
            return "warning"
        if now - self.last_success_at > timedelta(hours=24):
            return "stale"
        return "healthy"

    def stale_seconds(self, now: datetime) -> int | None:
        if self.last_success_at is None:
            return None
        return max(0, int((now - self.last_success_at).total_seconds()))

    def as_dict(self) -> dict[str, Any]:
        now = datetime.now(UTC)
        return {
            "last_attempt_at": self.last_attempt_at,
            "last_success_at": self.last_success_at,
            "last_error_at": self.last_error_at,
            "last_error": self.last_error,
            "health": self.health(now),
            "stale_seconds": self.stale_seconds(now),
            "last_removed_count": self.last_removed_count,
            "total_removed": self.total_removed,
            "runs": self.runs,
            "failures": self.failures,
        }


class MaintenanceStatusStore:
    def __init__(self) -> None:
        self._steps: dict[str, MaintenanceStepStatus] = {}
        self._lock = Lock()

    def mark_success(self, *, step_name: str, removed_count: int) -> None:
        now = datetime.now(UTC)
        with self._lock:
            status = self._steps.setdefault(step_name, MaintenanceStepStatus())
            status.last_attempt_at = now
            status.last_success_at = now
            status.last_error = None
            status.last_removed_count = max(0, int(removed_count))
            status.total_removed += max(0, int(removed_count))
            status.runs += 1

    def mark_error(self, *, step_name: str, error: Exception) -> None:
        now = datetime.now(UTC)
        with self._lock:
            status = self._steps.setdefault(step_name, MaintenanceStepStatus())
            status.last_attempt_at = now
            status.last_error_at = now
            status.last_error = str(error)
            status.failures += 1

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {name: state.as_dict() for name, state in self._steps.items()}


maintenance_status_store = MaintenanceStatusStore()
