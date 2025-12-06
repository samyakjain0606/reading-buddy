import os
import logging
import json
import datetime
import pytz
import random
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters
from agent import process_message

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    config = load_config()
    if config.get('chat_id') != chat_id:
        config['chat_id'] = chat_id
        save_config(config)
        
    await context.bot.send_message(chat_id=chat_id, text="I'm your Reading Buddy! Send me links or notes.")

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

async def send_morning_message(context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    chat_id = config.get('chat_id')
    
    if not chat_id:
        logging.warning("No chat_id found in config, cannot send morning message.")
        return

    # Ask Agent to generate the morning digest
    prompt = (
        "Look at the reading list. Pick the TOP 3 unread items. "
        "Generate a morning digest. For each item include: Title, Type, Tags, "
        "and a 1-sentence 'Why you should read this'. Format it nicely with emojis. "
        "Start with 'Good morning! Here is your daily reading digest:'"
    )
    response = await process_message(prompt, chat_id)
    await context.bot.send_message(chat_id=chat_id, text=response)

async def send_hydration_reminder(context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    chat_id = config.get('chat_id')
    if not chat_id: return

    # Ask Agent to generate the message
    prompt = (
        "Generate a short, witty reminder to drink water. "
        "ALSO, check the reading list and casually suggest ONE short or interesting item to read while hydrating. "
        "If the list is empty, just focus on the water."
    )
    response = await process_message(prompt, chat_id)
    await context.bot.send_message(chat_id=chat_id, text=response)

async def send_checkin(context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    chat_id = config.get('chat_id')
    if not chat_id: return

    # Ask Agent to generate the message
    prompt = "Look at the reading list. Pick ONE unread item. Generate a motivating message to read it NOW. Include the title, type, tags, and reasonable length reasoning. make it sound like a friend. If list is empty, congratulate me."
    response = await process_message(prompt, chat_id)
    await context.bot.send_message(chat_id=chat_id, text=response)

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        exit(1)
        
    application = Application.builder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    # Allow text AND photos
    message_handler = MessageHandler((filters.TEXT | filters.PHOTO) & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    # Schedule morning message
    job_queue = application.job_queue
    # 10:00 AM IST - Morning Digest
    time_morning = datetime.time(hour=10, minute=0, tzinfo=pytz.timezone('Asia/Kolkata'))
    job_queue.run_daily(send_morning_message, time=time_morning)

    # Hydration Reminders (11 AM, 2 PM, 5 PM, 8 PM)
    hydration_times = [11, 14, 17, 20]
    for hour in hydration_times:
        t = datetime.time(hour=hour, minute=0, tzinfo=pytz.timezone('Asia/Kolkata'))
        job_queue.run_daily(send_hydration_reminder, time=t)

    # Afternoon Check-in (3:30 PM)
    time_checkin = datetime.time(hour=15, minute=30, tzinfo=pytz.timezone('Asia/Kolkata'))
    job_queue.run_daily(send_checkin, time=time_checkin)
    
    print("Bot is running...")
    application.run_polling()
