"""Agent tools for managing cron jobs."""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Literal
import pytz

from .types import CronJob, Schedule
from .service import get_cron_service
from .schedule import format_schedule_for_display

logger = logging.getLogger(__name__)


def parse_relative_time(text: str) -> Optional[int]:
    """
    Parse relative time strings like "2h", "30m", "1d", "tomorrow 6pm".

    Returns timestamp in milliseconds, or None if can't parse.
    """
    text = text.lower().strip()
    tz = pytz.timezone("Asia/Kolkata")
    now = datetime.now(tz)

    # Handle "tomorrow at TIME"
    if text.startswith("tomorrow"):
        tomorrow = now + timedelta(days=1)
        time_part = text.replace("tomorrow", "").strip()
        if time_part.startswith("at "):
            time_part = time_part[3:]

        if time_part:
            # Try to parse time like "6pm", "18:00", "6:30pm"
            hour, minute = _parse_time_string(time_part)
            if hour is not None:
                result = tomorrow.replace(hour=hour, minute=minute or 0, second=0, microsecond=0)
                return int(result.timestamp() * 1000)

        # Default to 9am tomorrow
        result = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        return int(result.timestamp() * 1000)

    # Handle "today at TIME"
    if text.startswith("today"):
        time_part = text.replace("today", "").strip()
        if time_part.startswith("at "):
            time_part = time_part[3:]

        if time_part:
            hour, minute = _parse_time_string(time_part)
            if hour is not None:
                result = now.replace(hour=hour, minute=minute or 0, second=0, microsecond=0)
                if result <= now:
                    result += timedelta(days=1)
                return int(result.timestamp() * 1000)

    # Handle simple durations like "2h", "30m", "1d"
    match = re.match(r'^(\d+)\s*(h|hour|hours|m|min|mins|minutes|d|day|days|s|sec|seconds?)$', text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)[0]  # First char: h, m, d, s

        if unit == 'h':
            delta = timedelta(hours=value)
        elif unit == 'm':
            delta = timedelta(minutes=value)
        elif unit == 'd':
            delta = timedelta(days=value)
        elif unit == 's':
            delta = timedelta(seconds=value)
        else:
            return None

        result = now + delta
        return int(result.timestamp() * 1000)

    # Handle "in X hours/minutes"
    match = re.match(r'^in\s+(\d+)\s*(h|hour|hours|m|min|mins|minutes|d|day|days)$', text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)[0]

        if unit == 'h':
            delta = timedelta(hours=value)
        elif unit == 'm':
            delta = timedelta(minutes=value)
        elif unit == 'd':
            delta = timedelta(days=value)
        else:
            return None

        result = now + delta
        return int(result.timestamp() * 1000)

    return None


def _parse_time_string(text: str) -> tuple[Optional[int], Optional[int]]:
    """Parse time string like "6pm", "18:00", "6:30pm". Returns (hour, minute)."""
    text = text.lower().strip()

    # Handle "6pm", "6am"
    match = re.match(r'^(\d{1,2})\s*(am|pm)$', text)
    if match:
        hour = int(match.group(1))
        period = match.group(2)
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        return (hour, 0)

    # Handle "6:30pm", "6:30am"
    match = re.match(r'^(\d{1,2}):(\d{2})\s*(am|pm)$', text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        period = match.group(3)
        if period == 'pm' and hour != 12:
            hour += 12
        elif period == 'am' and hour == 12:
            hour = 0
        return (hour, minute)

    # Handle "18:00", "6:30"
    match = re.match(r'^(\d{1,2}):(\d{2})$', text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        return (hour, minute)

    return (None, None)


def parse_interval(text: str) -> Optional[int]:
    """
    Parse interval strings like "2h", "30m", "1d".

    Returns interval in milliseconds, or None if can't parse.
    """
    text = text.lower().strip()

    match = re.match(r'^(\d+)\s*(h|hour|hours|m|min|mins|minutes|d|day|days|s|sec|seconds?)$', text)
    if match:
        value = int(match.group(1))
        unit = match.group(2)[0]

        if unit == 'h':
            return value * 60 * 60 * 1000
        elif unit == 'm':
            return value * 60 * 1000
        elif unit == 'd':
            return value * 24 * 60 * 60 * 1000
        elif unit == 's':
            return value * 1000

    return None


def parse_daily_time(text: str) -> Optional[str]:
    """
    Parse daily time string to cron expression.

    Input: "8am", "10:30am", "18:00"
    Output: cron expression like "0 8 * * *"
    """
    hour, minute = _parse_time_string(text)
    if hour is not None:
        return f"{minute or 0} {hour} * * *"
    return None


# ============================================================
# Agent Tools
# ============================================================

def cron_list() -> str:
    """
    List all scheduled reminders/jobs.

    Returns a formatted string showing all jobs with their schedules.
    """
    service = get_cron_service()
    if service is None:
        return "Scheduler not initialized"

    jobs = service.list_jobs()
    if not jobs:
        return "No reminders scheduled"

    lines = []
    for job in jobs:
        status = "on" if job.enabled else "off"
        schedule_str = format_schedule_for_display(job.schedule)
        next_run = ""
        if job.state.next_run_at_ms:
            dt = datetime.fromtimestamp(job.state.next_run_at_ms / 1000)
            next_run = f" (next: {dt.strftime('%b %d %I:%M %p')})"

        lines.append(f"- [{job.id}] {job.name} | {schedule_str} | {status}{next_run}")

    return "Scheduled reminders:\n" + "\n".join(lines)


def cron_add(
    name: str,
    prompt: str,
    schedule_type: Literal["at", "every", "daily"],
    schedule_value: str,
    delete_after_run: bool = False
) -> str:
    """
    Create a new scheduled reminder/job.

    Args:
        name: Short name for the reminder (e.g., "Water reminder")
        prompt: What to do when triggered (e.g., "remind samyak to drink water")
        schedule_type: "at" for one-shot, "every" for interval, "daily" for fixed time
        schedule_value: Time value based on type:
            - at: "2h", "tomorrow 6pm", "in 30 minutes"
            - every: "2h", "30m"
            - daily: "8am", "10:30am", "18:00"
        delete_after_run: If True, delete after first execution (for one-shot reminders)

    Returns:
        Success/failure message
    """
    service = get_cron_service()
    if service is None:
        return "Scheduler not initialized"

    # Build schedule based on type
    if schedule_type == "at":
        at_ms = parse_relative_time(schedule_value)
        if at_ms is None:
            return f"Couldn't parse time '{schedule_value}'. Try '2h', 'tomorrow 6pm', 'in 30 minutes'"
        schedule = Schedule(kind="at", at_ms=at_ms)
        delete_after_run = True  # One-shot reminders always delete

    elif schedule_type == "every":
        every_ms = parse_interval(schedule_value)
        if every_ms is None:
            return f"Couldn't parse interval '{schedule_value}'. Try '2h', '30m', '1d'"
        schedule = Schedule(kind="every", every_ms=every_ms)

    elif schedule_type == "daily":
        cron_expr = parse_daily_time(schedule_value)
        if cron_expr is None:
            return f"Couldn't parse time '{schedule_value}'. Try '8am', '10:30am', '18:00'"
        schedule = Schedule(kind="cron", expr=cron_expr)

    else:
        return f"Unknown schedule type: {schedule_type}"

    # Create job
    job = CronJob(
        id=CronJob.new_id(),
        name=name,
        prompt=prompt,
        schedule=schedule,
        delete_after_run=delete_after_run
    )

    service.add_job(job)

    schedule_str = format_schedule_for_display(schedule)
    return f"Created reminder '{name}' ({schedule_str})"


def cron_remove(job_id: str) -> str:
    """
    Remove a scheduled job by ID.

    Args:
        job_id: The job ID to remove (from cron_list output)

    Returns:
        Success/failure message
    """
    service = get_cron_service()
    if service is None:
        return "Scheduler not initialized"

    job = service.get_job(job_id)
    if job is None:
        return f"No job found with ID '{job_id}'"

    name = job.name
    if service.remove_job(job_id):
        return f"Removed reminder '{name}'"
    else:
        return f"Failed to remove job '{job_id}'"


def cron_update(
    job_id: str,
    enabled: Optional[bool] = None,
    name: Optional[str] = None
) -> str:
    """
    Update a scheduled job.

    Args:
        job_id: The job ID to update
        enabled: Set to True/False to enable/disable
        name: New name for the job

    Returns:
        Success/failure message
    """
    service = get_cron_service()
    if service is None:
        return "Scheduler not initialized"

    job = service.get_job(job_id)
    if job is None:
        return f"No job found with ID '{job_id}'"

    updates = {}
    if enabled is not None:
        updates["enabled"] = enabled
    if name is not None:
        updates["name"] = name

    if not updates:
        return "Nothing to update"

    job = service.update_job(job_id, **updates)
    if job:
        status = "enabled" if job.enabled else "disabled"
        return f"Updated '{job.name}' ({status})"
    else:
        return f"Failed to update job '{job_id}'"
