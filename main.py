import os
import logging
import json
import datetime
import pytz
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
    user_message = update.message.text
    chat_id = update.effective_chat.id
    
    # Save chat_id if not already saved
    config = load_config()
    if config.get('chat_id') != chat_id:
        config['chat_id'] = chat_id
        save_config(config)
    
    # Process message with Claude Agent
    response = await process_message(user_message, chat_id)
    
    await context.bot.send_message(chat_id=chat_id, text=response)

async def send_morning_message(context: ContextTypes.DEFAULT_TYPE):
    config = load_config()
    chat_id = config.get('chat_id')
    
    if not chat_id:
        logging.warning("No chat_id found in config, cannot send morning message.")
        return

    try:
        with open('reading_list.json', 'r') as f:
            reading_list = json.load(f)
            
        unread_items = [item for item in reading_list if item.get('status') == 'unread']
        
        if not unread_items:
            await context.bot.send_message(chat_id=chat_id, text="Good morning! Your reading list is empty. Great job staying on top of things!")
            return
            
        # Pick top 3 items
        items_to_send = unread_items[:3]
        
        message = "Good morning! Here are 3 things for you to read today:\n\n"
        for i, item in enumerate(items_to_send, 1):
            message += f"{i}. {item.get('description', 'No description')} - {item.get('url')}\n"
            
        await context.bot.send_message(chat_id=chat_id, text=message)
        
    except Exception as e:
        logging.error(f"Error sending morning message: {e}")

if __name__ == '__main__':
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        exit(1)
        
    application = Application.builder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    # Schedule morning message
    job_queue = application.job_queue
    # 10:00 AM IST
    time_ist = datetime.time(hour=10, minute=0, tzinfo=pytz.timezone('Asia/Kolkata'))
    job_queue.run_daily(send_morning_message, time=time_ist)
    
    print("Bot is running...")
    application.run_polling()
