import logging
import json
import os
import shutil
import datetime
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock, ToolResultBlock
from dotenv import load_dotenv

load_dotenv()

# Remove ANTHROPIC_API_KEY if it's the placeholder, as it conflicts with 'claude login'
if os.getenv('ANTHROPIC_API_KEY') == 'your_anthropic_api_key':
    os.environ.pop('ANTHROPIC_API_KEY', None)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure reading list exists
if not os.path.exists('reading_list.json'):
    with open('reading_list.json', 'w') as f:
        json.dump([], f)

async def process_message(user_message, chat_id):
    # Get absolute path to reading list
    reading_list_path = os.path.abspath('reading_list.json')

    # Get current time for the prompt
    current_time = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # System prompt to give the agent personality and context
    system_prompt = f"""You are a helpful Reading Buddy. Your goal is to curate a reading list for the user.
    The reading list is stored in '{reading_list_path}'.
    The current time is {current_time}.
    
    When the user sends a link:
    1. Read '{reading_list_path}'.
    2. Add the new item with fields: url, description, reason, added_at (use '{current_time}'), status='unread'.
    3. Write the updated list back to '{reading_list_path}'.
    4. Confirm to the user that it was added.

    When the user asks for their list:
    1. Read '{reading_list_path}'.
    2. Format the list nicely for the user.

    Be encouraging and concise and reply in telegram message format style, not markdown."""

    # Force use of system-installed claude to avoid unauthenticated bundled version
    cli_path = shutil.which("claude")
    if not cli_path:
        # Fallback to hardcoded path if not in PATH (based on previous discovery)
        cli_path = "/Users/sjain/.nvm/versions/node/v22.20.0/bin/claude"

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=["Read", "Write", "Edit"],
        permission_mode="acceptEdits",
        cwd="/Users/sjain/reading-buddy",
        max_turns=10,  # Allow enough turns for file operations
        cli_path=cli_path
    )

    final_response = ""
    
    logger.info(f"Processing message from chat_id {chat_id}: {user_message}")

    try:
        # The query function yields messages from the agent
        async for message in query(prompt=user_message, options=options):
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
        return f"Sorry, I encountered an error: {str(e)}"

    return final_response
