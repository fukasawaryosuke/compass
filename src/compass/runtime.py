from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from uuid import uuid4


class VaultLockedError(RuntimeError):
    """Raised when another compass operation owns the Vault write lock."""


def default_runtime_root() -> Path:
    return Path(__file__).resolve().parents[2] / ".runtime"


@dataclass
class Run:
    operation: str
    runtime_root: Path = field(default_factory=default_runtime_root)
    run_id: str = field(
        default_factory=lambda: f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}"
    )
    _started_at: datetime | None = field(default=None, init=False)
    _summary: dict[str, int] = field(default_factory=dict, init=False)
    _details: dict[str, object] = field(default_factory=dict, init=False)
    _lock_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self._lock_path = self.runtime_root / "locks" / "vault.lock"

    def __enter__(self) -> "Run":
        self.runtime_root.joinpath("runs").mkdir(parents=True, exist_ok=True)
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            descriptor = os.open(self._lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            raise VaultLockedError(
                f"Another compass operation is active. Remove stale lock only after confirming it is not running: {self._lock_path}"
            ) from error
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(self.run_id)
        self._started_at = datetime.now(UTC)
        return self

    def add_summary(self, **counts: int) -> None:
        for key, value in counts.items():
            self._summary[key] = self._summary.get(key, 0) + value

    def add_details(self, **details: object) -> None:
        """Store minimal operation metadata in the local, untracked run record."""
        self._details.update(details)

    def __exit__(self, exception_type: object, exception: object, traceback: object) -> None:
        finished_at = datetime.now(UTC)
        status = "failed" if exception_type else "succeeded"
        record = {
            "run_id": self.run_id,
            "operation": self.operation,
            "status": status,
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "finished_at": finished_at.isoformat(),
            "summary": self._summary,
            **self._details,
        }
        (self.runtime_root / "runs" / f"{self.run_id}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if self._lock_path.exists() and self._lock_path.read_text(encoding="utf-8") == self.run_id:
            self._lock_path.unlink()
