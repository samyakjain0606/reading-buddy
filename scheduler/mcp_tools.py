"""MCP tools for the scheduler - used by Claude Agent SDK."""

from typing import Any
from claude_agent_sdk import tool, create_sdk_mcp_server

from .tools import cron_list, cron_add, cron_remove, cron_update


@tool("cron_list", "List all scheduled reminders and jobs. Returns job IDs, names, schedules, and next run times.", {})
async def cron_list_tool(args: dict[str, Any]) -> dict[str, Any]:
    """List all scheduled reminders."""
    result = cron_list()
    return {
        "content": [{"type": "text", "text": result}]
    }


@tool(
    "cron_add",
    "Create a new scheduled reminder or job. Use schedule_type='at' for one-shot reminders (e.g., 'tomorrow 6pm', '2h'), 'every' for recurring intervals (e.g., '2h', '30m'), or 'daily' for fixed daily times (e.g., '8am', '10:30am').",
    {
        "name": str,
        "prompt": str,
        "schedule_type": str,
        "schedule_value": str
    }
)
async def cron_add_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Create a new scheduled reminder."""
    result = cron_add(
        name=args["name"],
        prompt=args["prompt"],
        schedule_type=args["schedule_type"],
        schedule_value=args["schedule_value"],
        delete_after_run=(args["schedule_type"] == "at")  # One-shot reminders auto-delete
    )
    return {
        "content": [{"type": "text", "text": result}]
    }


@tool(
    "cron_remove",
    "Remove/cancel a scheduled reminder by its job ID. Get the job ID from cron_list first.",
    {"job_id": str}
)
async def cron_remove_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Remove a scheduled reminder."""
    result = cron_remove(args["job_id"])
    return {
        "content": [{"type": "text", "text": result}]
    }


@tool(
    "cron_update",
    "Update a scheduled reminder - enable/disable it or change its name. Get the job ID from cron_list first.",
    {
        "job_id": str,
        "enabled": bool,
    }
)
async def cron_update_tool(args: dict[str, Any]) -> dict[str, Any]:
    """Update a scheduled reminder."""
    result = cron_update(
        job_id=args["job_id"],
        enabled=args.get("enabled"),
        name=args.get("name")
    )
    return {
        "content": [{"type": "text", "text": result}]
    }


def create_scheduler_mcp_server():
    """Create and return the scheduler MCP server with all cron tools."""
    return create_sdk_mcp_server(
        name="scheduler",
        version="1.0.0",
        tools=[cron_list_tool, cron_add_tool, cron_remove_tool, cron_update_tool]
    )
