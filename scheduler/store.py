"""Persistence layer for cron jobs."""

import json
import os
import tempfile
import logging
from typing import List
from .types import CronJob

logger = logging.getLogger(__name__)

STORE_VERSION = 1


def load_cron_store(path: str) -> List[CronJob]:
    """Load jobs from JSON file. Returns empty list if file missing or invalid."""
    if not os.path.exists(path):
        logger.info(f"Cron store not found at {path}, starting fresh")
        return []

    try:
        with open(path, 'r') as f:
            data = json.load(f)

        version = data.get("version", 1)
        if version != STORE_VERSION:
            logger.warning(f"Store version mismatch: {version} != {STORE_VERSION}")

        jobs = [CronJob.from_dict(j) for j in data.get("jobs", [])]
        logger.info(f"Loaded {len(jobs)} jobs from {path}")
        return jobs
    except Exception as e:
        logger.error(f"Error loading cron store: {e}")
        return []


def save_cron_store(jobs: List[CronJob], path: str) -> bool:
    """Atomically save jobs to JSON file. Returns True on success."""
    try:
        data = {
            "version": STORE_VERSION,
            "jobs": [j.to_dict() for j in jobs]
        }

        # Atomic write: write to temp file, then rename
        dir_path = os.path.dirname(path) or '.'
        fd, temp_path = tempfile.mkstemp(dir=dir_path, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.rename(temp_path, path)
            logger.info(f"Saved {len(jobs)} jobs to {path}")
            return True
        except:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except Exception as e:
        logger.error(f"Error saving cron store: {e}")
        return False
