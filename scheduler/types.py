"""Data types for the cron/scheduling system."""

from dataclasses import dataclass, field
from typing import Optional, Literal
import time
import uuid


@dataclass
class Schedule:
    """Represents when a job should run."""
    kind: Literal["at", "every", "cron"]  # at=one-shot, every=interval, cron=cron expression
    at_ms: Optional[int] = None           # Timestamp for one-shot jobs
    every_ms: Optional[int] = None        # Interval in ms for recurring jobs
    expr: Optional[str] = None            # Cron expression (e.g., "0 10 * * *")
    tz: str = "Asia/Kolkata"              # Timezone for schedule

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "at_ms": self.at_ms,
            "every_ms": self.every_ms,
            "expr": self.expr,
            "tz": self.tz
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        return cls(
            kind=data["kind"],
            at_ms=data.get("at_ms"),
            every_ms=data.get("every_ms"),
            expr=data.get("expr"),
            tz=data.get("tz", "Asia/Kolkata")
        )


@dataclass
class JobState:
    """Runtime state of a job."""
    next_run_at_ms: Optional[int] = None
    last_run_at_ms: Optional[int] = None
    last_status: Optional[Literal["ok", "error"]] = None
    last_error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "next_run_at_ms": self.next_run_at_ms,
            "last_run_at_ms": self.last_run_at_ms,
            "last_status": self.last_status,
            "last_error": self.last_error
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobState":
        return cls(
            next_run_at_ms=data.get("next_run_at_ms"),
            last_run_at_ms=data.get("last_run_at_ms"),
            last_status=data.get("last_status"),
            last_error=data.get("last_error")
        )


@dataclass
class CronJob:
    """A scheduled job."""
    id: str
    name: str
    prompt: str
    schedule: Schedule
    enabled: bool = True
    delete_after_run: bool = False  # For one-shot reminders
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    state: JobState = field(default_factory=JobState)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "schedule": self.schedule.to_dict(),
            "enabled": self.enabled,
            "delete_after_run": self.delete_after_run,
            "created_at_ms": self.created_at_ms,
            "state": self.state.to_dict()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CronJob":
        return cls(
            id=data["id"],
            name=data["name"],
            prompt=data["prompt"],
            schedule=Schedule.from_dict(data["schedule"]),
            enabled=data.get("enabled", True),
            delete_after_run=data.get("delete_after_run", False),
            created_at_ms=data.get("created_at_ms", int(time.time() * 1000)),
            state=JobState.from_dict(data.get("state", {}))
        )

    @staticmethod
    def new_id() -> str:
        """Generate a short unique ID for a job."""
        return uuid.uuid4().hex[:8]
