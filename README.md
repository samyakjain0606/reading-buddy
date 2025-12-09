# Reading Buddy

A Telegram bot powered by Claude (via the Agent SDK) that acts as your personal reading list curator. Meet Gemi, a slightly sarcastic penguin who manages your reading backlog and keeps you hydrated.

## Features

- **Smart Link Curation**: Send any link and Gemi will automatically categorize it by type (article, video, repo, podcast, social) and add relevant tags
- **Reading List Management**: Track your reading backlog, mark items as read, and get recommendations
- **Streak Tracking**: Monitor your reading and collection streaks to build consistent habits
- **Scheduled Reminders**:
  - Morning digest (10 AM IST) - Top 3 unread items to tackle
  - Hydration reminders (11 AM, 2 PM, 5 PM, 8 PM IST) - Water breaks with reading suggestions
  - Afternoon check-in (3:30 PM IST) - Motivational nudge to read something
- **Photo Support**: Send screenshots or images with captions for the bot to process
- **Persistent Sessions**: Conversations maintain context with automatic memory compaction

## Tech Stack

- **Python** with `python-telegram-bot` for the Telegram interface
- **Claude Agent SDK** for AI-powered interactions
- **Claude Code CLI** for authentication

## Setup

### Prerequisites

- Python 3.11+
- Node.js (for Claude Code CLI)
- A Telegram bot token (get one from [@BotFather](https://t.me/BotFather))

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/samyakjain0606/reading-buddy.git
   cd reading-buddy
   ```

2. **Create virtual environment and install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Claude Code CLI**:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

4. **Authenticate with Claude**:
   ```bash
   claude login
   ```
   Follow the browser instructions to complete authentication.

5. **Configure environment**:
   Create a `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   ```
   Note: `ANTHROPIC_API_KEY` is not needed if you use `claude login`.

6. **Run the bot**:
   ```bash
   python main.py
   ```

## Usage

### Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and register your chat |
| `/stats` | View your reading list statistics |
| `/streak` | Check your reading and collection streaks |

### Natural Language Interactions

Just chat naturally with Gemi:
- Send a link to add it to your reading list
- "Show me my reading list" or "what do I have unread?"
- "Mark [article name] as read"
- "What should I read next?"
- "Show me AI-related articles"

### Example Interaction

```
You: https://example.com/some-great-article

Gemi: added. another ai thing huh 🐧 tagged ai, tools. you have 14 unread btw
```

## Project Structure

```
reading-buddy/
├── main.py              # Telegram bot entry point and handlers
├── agent.py             # Claude Agent SDK integration
├── system_prompt.txt    # Gemi's personality and behavior rules
├── reading_list.json    # Your reading list data (auto-created)
├── config.json          # Bot configuration (chat_id)
├── requirements.txt     # Python dependencies
└── FEATURES.md          # Future feature ideas
```

## Running as a Service (macOS)

A launchd plist (`com.sjain.readingbuddy.plist`) is included for running the bot as a background service on macOS.

## Contributing

Feel free to open issues or submit PRs. Check out `FEATURES.md` for planned enhancements and feature ideas.

## License

MIT
