"""Job executor: sends prompts to agent and delivers responses."""

import logging
from .types import CronJob

logger = logging.getLogger(__name__)

# These will be set by main.py
_process_message = None
_send_message = None
_chat_id = None


def set_executor_deps(process_message, send_message, chat_id_getter):
    """
    Set dependencies for job execution.

    Args:
        process_message: async function(prompt, chat_id) -> response
        send_message: async function(chat_id, text)
        chat_id_getter: function() -> chat_id
    """
    global _process_message, _send_message, _chat_id
    _process_message = process_message
    _send_message = send_message
    _chat_id = chat_id_getter


async def execute_cron_job(job: CronJob):
    """
    Execute a cron job by sending its prompt to the agent
    and delivering the response to Telegram.
    """
    if _process_message is None or _send_message is None or _chat_id is None:
        raise RuntimeError("Executor dependencies not configured")

    chat_id = _chat_id()
    if not chat_id:
        logger.warning(f"No chat_id configured, skipping job {job.id}")
        return

    logger.info(f"Executing job '{job.name}' with prompt: {job.prompt[:50]}...")

    # Send prompt to agent
    response = await _process_message(job.prompt, chat_id)

    # Send response to Telegram
    await _send_message(chat_id, response)

    logger.info(f"Job '{job.name}' executed successfully")
