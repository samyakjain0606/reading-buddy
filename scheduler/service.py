"""CronService: manages job lifecycle and timer scheduling."""

import logging
import time
import asyncio
from typing import Optional, List, Callable, Any
from .types import CronJob, Schedule, JobState
from .store import load_cron_store, save_cron_store
from .schedule import compute_next_run_at_ms

logger = logging.getLogger(__name__)

# Default store path
DEFAULT_STORE_PATH = "cron_jobs.json"


class CronService:
    """
    Manages scheduled jobs using a single-timer strategy.

    Instead of creating one timer per job, we maintain a single timer
    that fires at the next job's scheduled time. After execution,
    we re-arm the timer for the next earliest job.
    """

    def __init__(self, store_path: str = DEFAULT_STORE_PATH):
        self.store_path = store_path
        self.jobs: List[CronJob] = []
        self._timer_handle: Optional[asyncio.TimerHandle] = None
        self._executor: Optional[Callable] = None
        self._job_queue: Any = None  # Telegram job queue for scheduling
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._started = False

    def set_executor(self, executor: Callable):
        """Set the function to call when executing jobs."""
        self._executor = executor

    def set_job_queue(self, job_queue):
        """Set the Telegram job queue for scheduling."""
        self._job_queue = job_queue

    def start(self):
        """Load jobs and arm the timer."""
        self.jobs = load_cron_store(self.store_path)
        self._loop = asyncio.get_event_loop()
        self._started = True

        # Recompute next run times for all jobs
        now_ms = int(time.time() * 1000)
        for job in self.jobs:
            if job.enabled:
                job.state.next_run_at_ms = compute_next_run_at_ms(job.schedule, now_ms)

        self._save()
        self._arm_timer()
        logger.info(f"CronService started with {len(self.jobs)} jobs")

    def stop(self):
        """Cancel timer and save state."""
        self._started = False
        if self._timer_handle:
            self._timer_handle.cancel()
            self._timer_handle = None
        self._save()
        logger.info("CronService stopped")

    def add_job(self, job: CronJob) -> CronJob:
        """Add a new job and re-arm timer if needed."""
        now_ms = int(time.time() * 1000)
        job.state.next_run_at_ms = compute_next_run_at_ms(job.schedule, now_ms)

        self.jobs.append(job)
        self._save()
        self._arm_timer()

        logger.info(f"Added job {job.id}: {job.name}")
        return job

    def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID."""
        for i, job in enumerate(self.jobs):
            if job.id == job_id:
                del self.jobs[i]
                self._save()
                self._arm_timer()
                logger.info(f"Removed job {job_id}")
                return True
        return False

    def update_job(self, job_id: str, **kwargs) -> Optional[CronJob]:
        """Update a job's properties."""
        for job in self.jobs:
            if job.id == job_id:
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)

                # Recompute next run if schedule changed or job was enabled
                if "schedule" in kwargs or ("enabled" in kwargs and kwargs["enabled"]):
                    now_ms = int(time.time() * 1000)
                    job.state.next_run_at_ms = compute_next_run_at_ms(job.schedule, now_ms)

                self._save()
                self._arm_timer()
                logger.info(f"Updated job {job_id}")
                return job
        return None

    def get_job(self, job_id: str) -> Optional[CronJob]:
        """Get a job by ID."""
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    def list_jobs(self) -> List[CronJob]:
        """Return all jobs."""
        return self.jobs.copy()

    def _save(self):
        """Persist jobs to disk."""
        save_cron_store(self.jobs, self.store_path)

    def _arm_timer(self):
        """Schedule the next timer for the earliest job."""
        if not self._started:
            return

        # Cancel existing timer
        if self._timer_handle:
            self._timer_handle.cancel()
            self._timer_handle = None

        # Find next job to run
        now_ms = int(time.time() * 1000)
        next_job = None
        next_time = None

        for job in self.jobs:
            if not job.enabled:
                continue
            if job.state.next_run_at_ms is None:
                continue
            if next_time is None or job.state.next_run_at_ms < next_time:
                next_time = job.state.next_run_at_ms
                next_job = job

        if next_job is None:
            logger.debug("No jobs scheduled")
            return

        # Calculate delay
        delay_ms = max(0, next_time - now_ms)
        delay_sec = delay_ms / 1000

        # Use Telegram's job_queue if available (more reliable for long delays)
        if self._job_queue is not None:
            self._job_queue.run_once(
                self._on_timer_callback,
                when=delay_sec,
                name=f"cron_timer_{next_job.id}"
            )
            logger.debug(f"Armed timer via job_queue for {next_job.name} in {delay_sec:.1f}s")
        elif self._loop:
            # Fallback to asyncio timer
            self._timer_handle = self._loop.call_later(
                delay_sec,
                lambda: asyncio.create_task(self._on_timer())
            )
            logger.debug(f"Armed timer via asyncio for {next_job.name} in {delay_sec:.1f}s")

    async def _on_timer_callback(self, context):
        """Callback for Telegram job_queue."""
        await self._on_timer()

    async def _on_timer(self):
        """Called when timer fires. Execute due jobs and re-arm."""
        now_ms = int(time.time() * 1000)
        jobs_to_delete = []

        for job in self.jobs:
            if not job.enabled:
                continue
            if job.state.next_run_at_ms is None:
                continue
            if job.state.next_run_at_ms > now_ms:
                continue

            # Job is due - execute it
            logger.info(f"Executing job {job.id}: {job.name}")
            await self._execute_job(job)

            # Mark for deletion if one-shot
            if job.delete_after_run:
                jobs_to_delete.append(job.id)
            else:
                # Compute next run time
                job.state.next_run_at_ms = compute_next_run_at_ms(job.schedule, now_ms)

        # Delete one-shot jobs
        for job_id in jobs_to_delete:
            self.remove_job(job_id)

        self._save()
        self._arm_timer()

    async def _execute_job(self, job: CronJob):
        """Execute a single job."""
        job.state.last_run_at_ms = int(time.time() * 1000)

        if self._executor is None:
            logger.warning("No executor set, skipping job execution")
            job.state.last_status = "error"
            job.state.last_error = "No executor configured"
            return

        try:
            await self._executor(job)
            job.state.last_status = "ok"
            job.state.last_error = None
        except Exception as e:
            logger.error(f"Error executing job {job.id}: {e}")
            job.state.last_status = "error"
            job.state.last_error = str(e)


# Global service instance (set by main.py)
_cron_service: Optional[CronService] = None


def get_cron_service() -> Optional[CronService]:
    """Get the global CronService instance."""
    return _cron_service


def set_cron_service(service: CronService):
    """Set the global CronService instance."""
    global _cron_service
    _cron_service = service
