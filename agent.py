import logging
import json
import os
import shutil
import datetime
from claude_agent_sdk import ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock, ToolResultBlock, ClaudeSDKClient
from dotenv import load_dotenv

load_dotenv()

# Import scheduler MCP server
from scheduler.mcp_tools import create_scheduler_mcp_server

# Remove ANTHROPIC_API_KEY if it's the placeholder, as it conflicts with 'claude login'
if os.getenv('ANTHROPIC_API_KEY') == 'your_anthropic_api_key':
    os.environ.pop('ANTHROPIC_API_KEY', None)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure reading list exists
if not os.path.exists('reading_list.json'):
    with open('reading_list.json', 'w') as f:
        json.dump([], f)

# Create scheduler MCP server (singleton)
SCHEDULER_MCP_SERVER = create_scheduler_mcp_server()

# Tools configuration
ALLOWED_TOOLS = [
    "Read", "Write", "Edit", "WebFetch",
    "mcp__scheduler__cron_list",
    "mcp__scheduler__cron_add",
    "mcp__scheduler__cron_remove",
    "mcp__scheduler__cron_update"
]

# Global dictionary to store sessions: {chat_id: {'client': ClaudeSDKClient, 'turn_count': int}}
SESSIONS = {}
TURN_LIMIT = 20


def create_agent_options(system_prompt: str, cli_path: str) -> ClaudeAgentOptions:
    """Create ClaudeAgentOptions with scheduler MCP server."""
    return ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=ALLOWED_TOOLS,
        mcp_servers={"scheduler": SCHEDULER_MCP_SERVER},
        permission_mode="acceptEdits",
        cwd="/Users/sjain/gemi",
        max_turns=10,
        cli_path=cli_path
    )


async def get_or_create_session(chat_id, system_prompt, cli_path):
    if chat_id not in SESSIONS:
        logger.info(f"🆕 Creating NEW session for chat_id {chat_id}")
        options = create_agent_options(system_prompt, cli_path)
        client = ClaudeSDKClient(options)
        await client.connect()
        SESSIONS[chat_id] = {'client': client, 'turn_count': 0}
    else:
        logger.info(f"♻️  REUSING existing session for chat_id {chat_id} (turn #{SESSIONS[chat_id]['turn_count'] + 1})")

    return SESSIONS[chat_id]


async def compact_session(chat_id, session):
    client = session['client']
    logger.info(f"Compacting session for chat_id {chat_id} (turns > {TURN_LIMIT})")

    # 1. Summarize
    summary_prompt = "CRITICAL: Summarize our current conversation state, known user preferences, and any unfinished tasks in 2-3 sentences. Do not add any conversational filler."
    summary = ""
    try:
        await client.query(summary_prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        summary += block.text
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        summary = "Previous context lost due to error."

    logger.info(f"Session Summary: {summary}")

    # 2. Disconnect old client
    try:
        await client.disconnect()
    except Exception as e:
        logger.error(f"Error disconnecting client: {e}")

    # 3. Create NEW client with fresh system prompt
    reading_list_path = os.path.abspath('reading_list.json')
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
        with open('system_prompt.txt', 'r') as f:
            template = f.read()
            base_prompt = template.format(
                reading_list_path=reading_list_path,
                current_time=current_time
            )
    except:
        base_prompt = f"You are a helpful assistant. The current time is {current_time}."

    # Inject summary into new system prompt
    new_system_prompt = f"{base_prompt}\n\n[PREVIOUS CONVERSATION SUMMARY]: {summary}"

    cli_path = shutil.which("claude") or "/Users/sjain/.nvm/versions/node/v22.20.0/bin/claude"

    options = create_agent_options(new_system_prompt, cli_path)
    new_client = ClaudeSDKClient(options)
    await new_client.connect()

    # Update session
    SESSIONS[chat_id] = {'client': new_client, 'turn_count': 0}
    logger.info(f"Session compacted and reset for chat_id {chat_id}")
    return SESSIONS[chat_id]


async def process_message(user_message, chat_id, image_path=None):
    # Get absolute path to reading list
    reading_list_path = os.path.abspath('reading_list.json')

    # Get current time for the prompt
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # System prompt loading
    try:
        with open('system_prompt.txt', 'r') as f:
            template = f.read()
            system_prompt = template.format(
                reading_list_path=reading_list_path,
                current_time=current_time
            )
    except Exception as e:
        logger.error(f"Error reading system prompt: {e}")
        system_prompt = f"You are a helpful assistant. The current time is {current_time}."

    # Force use of system-installed claude
    cli_path = shutil.which("claude")
    if not cli_path:
        cli_path = "/Users/sjain/.nvm/versions/node/v22.20.0/bin/claude"

    # Get or create session
    session = await get_or_create_session(chat_id, system_prompt, cli_path)

    # Check for compaction
    if session['turn_count'] >= TURN_LIMIT:
        await session['client'].query("Hold on, my memory is getting full. Organizing my thoughts...")
        async for _ in session['client'].receive_response():
            pass
        session = await compact_session(chat_id, session)

    client = session['client']

    # Append image info to user message if present
    if image_path:
        user_message += f"\n\n[System Note: The user has uploaded an image. It is saved locally at '{image_path}'. Please analyze this image if relevant to the request. If you cannot read images directly, please let the user know.]"

    final_response = ""
    logger.info(f"Processing message from chat_id {chat_id}: {user_message}")

    try:
        # Send query to existing session
        await client.query(user_message)
        session['turn_count'] += 1

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        final_response += block.text
                    elif isinstance(block, ToolUseBlock):
                        logger.info(f"Agent using tool: {block.name} input: {block.input}")
                    elif isinstance(block, ToolResultBlock):
                        logger.info(f"Tool result: {block.content} (is_error={block.is_error})")
                    else:
                        logger.info(f"Agent generated block type: {type(block)}")

        logger.info(f"Agent response for chat_id {chat_id}: {final_response}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # If session is broken, clear it so next time it recreates
        if chat_id in SESSIONS:
            del SESSIONS[chat_id]
        return f"Sorry, I encountered an error: {str(e)}"

    return final_response
