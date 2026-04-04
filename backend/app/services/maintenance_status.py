from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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

    def as_dict(self) -> dict[str, Any]:
        return {
            "last_attempt_at": self.last_attempt_at,
            "last_success_at": self.last_success_at,
            "last_error_at": self.last_error_at,
            "last_error": self.last_error,
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
