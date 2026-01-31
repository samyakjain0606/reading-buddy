"""Schedule computation for next run times."""

import logging
from datetime import datetime
from typing import Optional
import pytz

logger = logging.getLogger(__name__)


def compute_next_run_at_ms(schedule, now_ms: int) -> Optional[int]:
    """
    Calculate the next run time in milliseconds.

    Args:
        schedule: Schedule object with kind, at_ms, every_ms, or expr
        now_ms: Current time in milliseconds

    Returns:
        Next run time in ms, or None if job shouldn't run again
    """
    kind = schedule.kind
    tz = pytz.timezone(schedule.tz)

    if kind == "at":
        # One-shot: return timestamp if in future, else None
        if schedule.at_ms and schedule.at_ms > now_ms:
            return schedule.at_ms
        return None

    elif kind == "every":
        # Interval: round up to next interval from now
        if not schedule.every_ms or schedule.every_ms <= 0:
            return None

        interval = schedule.every_ms
        # Next run is now rounded up to next interval boundary
        next_run = ((now_ms // interval) + 1) * interval
        return next_run

    elif kind == "cron":
        # Cron expression: use croniter
        if not schedule.expr:
            return None

        try:
            from croniter import croniter

            # Convert now_ms to datetime in the schedule's timezone
            now_dt = datetime.fromtimestamp(now_ms / 1000, tz=tz)

            # Get next run time
            cron = croniter(schedule.expr, now_dt)
            next_dt = cron.get_next(datetime)

            # Convert back to ms
            return int(next_dt.timestamp() * 1000)
        except ImportError:
            logger.error("croniter not installed, cron expressions won't work")
            return None
        except Exception as e:
            logger.error(f"Error computing cron next run: {e}")
            return None

    else:
        logger.warning(f"Unknown schedule kind: {kind}")
        return None


def format_schedule_for_display(schedule) -> str:
    """Format a schedule for human-readable display."""
    kind = schedule.kind

    if kind == "at":
        if schedule.at_ms:
            dt = datetime.fromtimestamp(schedule.at_ms / 1000)
            return f"once at {dt.strftime('%b %d %I:%M %p')}"
        return "once (time not set)"

    elif kind == "every":
        if schedule.every_ms:
            ms = schedule.every_ms
            if ms >= 86400000:  # days
                return f"every {ms // 86400000}d"
            elif ms >= 3600000:  # hours
                return f"every {ms // 3600000}h"
            elif ms >= 60000:  # minutes
                return f"every {ms // 60000}m"
            else:
                return f"every {ms // 1000}s"
        return "every ??? "

    elif kind == "cron":
        return f"cron: {schedule.expr}"

    return f"unknown: {kind}"
