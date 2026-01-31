import os
import logging
import json
import datetime
from collections import Counter
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from agent import process_message

# Import scheduler
from scheduler.service import CronService, set_cron_service
from scheduler.executor import set_executor_deps, execute_cron_job

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"chat_id": None}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def calculate_streak(dates_strings):
    """Calculates current streak of consecutive days from a list of date strings."""
    if not dates_strings:
        return 0
    
    # Parse dates and notify time info to get just date objects
    dates = set()
    for ds in dates_strings:
        try:
            # Handle ISO format with possible Z or timezone
            dt = datetime.datetime.fromisoformat(ds.replace('Z', '+00:00'))
            dates.add(dt.date())
        except ValueError:
            continue
            
    if not dates:
        return 0
        
    sorted_dates = sorted(list(dates), reverse=True)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    
    current_streak = 0
    check_date = today
    
    # Check if today is present, if not check yesterday (streak might be active but not incremented today yet)
    if check_date not in sorted_dates:
        check_date = today - datetime.timedelta(days=1)
        if check_date not in sorted_dates:
            return 0 # Streak broken or not started
            
    # Count backwards
    while check_date in sorted_dates:
        current_streak += 1
        check_date -= datetime.timedelta(days=1)
        
    return current_streak

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    config = load_config()
    if config.get('chat_id') != chat_id:
        config['chat_id'] = chat_id
        save_config(config)
        
    await context.bot.send_message(chat_id=chat_id, text="I'm your Reading Buddy! Send me links or notes.")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        if not os.path.exists('reading_list.json'):
             await context.bot.send_message(chat_id=chat_id, text="No reading list found yet!")
             return

        with open('reading_list.json', 'r') as f:
            reading_list = json.load(f)
            
        total_items = len(reading_list)
        read_count = sum(1 for item in reading_list if item.get('status') == 'read')
        unread_count = total_items - read_count
        
        # Tags stats
        all_tags = []
        for item in reading_list:
            all_tags.extend(item.get('tags', []))
        
        top_tags = Counter(all_tags).most_common(5)
        tags_str = "\n".join([f"#{tag} ({count})" for tag, count in top_tags])
        
        msg = (
            f"📊 **My Library Stats**\n\n"
            f"📚 Total Items: {total_items}\n"
            f"✅ Read: {read_count}\n"
            f"📖 To Read: {unread_count}\n\n"
            f"🏷️ **Top Topics:**\n{tags_str}"
        )
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Error in stats: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Oops, couldn't calculate stats right now.")

async def streak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        if not os.path.exists('reading_list.json'):
             await context.bot.send_message(chat_id=chat_id, text="No reading list found yet!")
             return

        with open('reading_list.json', 'r') as f:
            reading_list = json.load(f)
            
        # Collection Streak (based on added_at)
        added_dates = [item.get('added_at') for item in reading_list if item.get('added_at')]
        collection_streak = calculate_streak(added_dates)
        
        # Reading Streak (based on read_at)
        read_dates = [item.get('read_at') for item in reading_list if item.get('read_at')]
        reading_streak = calculate_streak(read_dates)
        
        msg = (
            f"🔥 **Streaks**\n\n"
            f"📖 **Reading Streak:** {reading_streak} days\n"
            f"_(Days you finished an article)_\n\n"
            f"📥 **Collection Streak:** {collection_streak} days\n"
            f"_(Days you added new stuff)_"
        )
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Error in streak: {e}")
        await context.bot.send_message(chat_id=chat_id, text="Oops, couldn't calculate streaks right now.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    image_path = None
    
    # Handle both text and photos
    if update.message.photo:
        caption = update.message.caption or ""
        user_message = f"I sent a photo. Caption: {caption}" if caption else "I sent a photo."
        
        # Download the photo
        photo = await update.message.photo[-1].get_file()
        # Ensure photos directory exists
        os.makedirs('photos', exist_ok=True)
        image_path = os.path.abspath(f'photos/{update.message.message_id}.jpg')
        await photo.download_to_drive(image_path)
        
    elif update.message.text:
        user_message = update.message.text
    else:
        return

    # Save chat_id if not already saved
    config = load_config()
    if config.get('chat_id') != chat_id:
        config['chat_id'] = chat_id
        save_config(config)
    
    # Process message with Claude Agent
    response = await process_message(user_message, chat_id, image_path)
    
    await context.bot.send_message(chat_id=chat_id, text=response)

async def post_init(application: Application):
    """Initialize scheduler after application is ready."""
    config = load_config()

    # Helper to get chat_id
    def get_chat_id():
        return config.get('chat_id')

    # Helper to send message
    async def send_message(chat_id, text):
        await application.bot.send_message(chat_id=chat_id, text=text)

    # Set up executor dependencies
    set_executor_deps(process_message, send_message, get_chat_id)

    # Create and start cron service
    cron_service = CronService(store_path="cron_jobs.json")
    cron_service.set_executor(execute_cron_job)
    cron_service.set_job_queue(application.job_queue)
    cron_service.start()

    # Make service globally available
    set_cron_service(cron_service)

    logging.info("Scheduler initialized")


if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        exit(1)

    application = Application.builder().token(token).post_init(post_init).build()

    start_handler = CommandHandler('start', start)
    stats_handler = CommandHandler('stats', stats_command)
    streak_handler = CommandHandler('streak', streak_command)

    # Allow text AND photos
    message_handler = MessageHandler((filters.TEXT | filters.PHOTO) & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(stats_handler)
    application.add_handler(streak_handler)
    application.add_handler(message_handler)

    print("Bot is running...")
    application.run_polling()
