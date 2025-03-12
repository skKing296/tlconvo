import requests
import json
import time
import os
import socketserver
import threading
import random
import asyncio
import pytz
from datetime import datetime
import dateutil.tz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from collections import defaultdict

# Telegram bot token
TELEGRAM_BOT_TOKEN = '7571197958:AAEfGnS1kXmiFuvwpIAKXWhbe4eR85pHawQ'

# Dictionary to track active SMS sending tasks for each user
active_tasks = {}

# List of approved keys - you can add more keys here
APPROVED_KEYS = ['syapaking', 'catoo', 'SYAPAKING', '7045', '4120']

# Your WhatsApp contact
WHATSAPP_CONTACT = '+92323704😹'

# Dictionary to track user approval status
user_approval_status = {}

# Dictionary to track user statistics
user_stats = defaultdict(lambda: {
    'messages_sent': 0,
    'last_activity': None,
    'running': False
})

class MyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(1024).strip()
        self.request.sendall(b"TRICKS BY AMIR")

def run_server():
    PORT = int(os.environ.get('PORT', 4000))
    server = socketserver.ThreadingTCPServer(("0.0.0.0", PORT), MyHandler)
    print(f"Server running on port {PORT}")
    server.serve_forever()

async def send_messages_from_file(token, tid, hater_name, speed, file_content, chat_id, context, user_id):
    message_count = 0
    headers = {"Content-Type": "application/json"}
    
    # Update user stats
    user_stats[user_id]['running'] = True
    user_stats[user_id]['last_activity'] = datetime.now(pytz.timezone('Asia/Karachi')).strftime("%Y-%m-%d %I:%M:%S %p")

    messages = [msg.strip() for msg in file_content.split('\n') if msg.strip()]

    try:
        while not context.user_data.get('stop_sending', False):
            for message in messages:
                # Check stop flag again between each message
                if context.user_data.get('stop_sending', False):
                    break

                # If this user's task has been canceled, exit
                if user_id not in active_tasks:
                    return {"status": "canceled", "messages_sent": message_count}

                url = f"https://graph.facebook.com/v17.0/{'t_' + tid}/"
                full_message = hater_name + ' ' + message
                parameters = {'access_token': token, 'message': full_message}

                try:
                    response = requests.post(url, json=parameters, headers=headers)
                    message_count += 1
                    current_time = time.strftime("%Y-%m-%d %I:%M:%S %p")
                    
                    status_message = ""
                    if response.ok:
                        status_message = f"✅ SMS SENT! {message_count} to Convo {tid}: {full_message}"
                        print(f"\033[1;92m[+] CHALA GEYA SMS ✅ {message_count} of Convo {tid}: {full_message}")
                        # Update user stats when message is sent successfully
                        user_stats[user_id]['messages_sent'] += 1
                    else:
                        status_message = f"❌ SMS FAILED! {message_count} to Convo {tid}: {full_message}"
                        print(f"\033[1;91m[x] MSG NAHI JA RAHA HAI ❌ {message_count} of Convo {tid}: {full_message}")

                    # Send real-time update to Telegram
                    if chat_id:
                        await context.bot.send_message(chat_id=chat_id, text=status_message)
                except Exception as e:
                    print(f"Error sending message: {str(e)}")
                    if chat_id:
                        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error sending message: {str(e)}")

                # Wait for specified speed between messages
                try:
                    speed_seconds = float(speed)
                    await asyncio.sleep(speed_seconds)
                except ValueError:
                    await asyncio.sleep(1)  # Default to 1 second if speed is invalid

        await context.bot.send_message(chat_id=chat_id, text=f"🛑 Stopped SMS sending after {message_count} messages.")
    except Exception as e:
        print(f"Error in send_messages: {str(e)}")
        if chat_id:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error in SMS loop: {str(e)}")
    finally:
        # Update user stats
        user_stats[user_id]['running'] = False
        user_stats[user_id]['last_activity'] = datetime.now(pytz.timezone('Asia/Karachi')).strftime("%Y-%m-%d %I:%M:%S %p")
        
        # Clean up active task reference
        if user_id in active_tasks:
            del active_tasks[user_id]
        return {"status": "completed", "messages_sent": message_count}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    # Reset any previous steps
    context.user_data.clear()
    
    # Welcome message with WhatsApp number
    welcome_message = f"""
*Welcome to the SYAPA convo BoT* 🤖

Hi {username}! This bot helps you send SMS messages.

For approval key, please contact on WhatsApp:
📱 *{WHATSAPP_CONTACT}*

You will receive your approval key on WhatsApp only after verification.
    """
    
    # Check if user is already approved
    if user_id in user_approval_status and user_approval_status[user_id]['approved']:
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        await update.message.reply_text('You are already approved. Send your token to start.')
        context.user_data['step'] = 'waiting_for_token'
    else:
        context.user_data['step'] = 'waiting_for_approval'
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        await update.message.reply_text('Please send your approval key to continue.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Check if user is approved
    if user_id not in user_approval_status or not user_approval_status[user_id]['approved']:
        await update.message.reply_text("You need to be approved to use this service. Use /start to begin the approval process.")
        return

    help_text = """
Send me your token, TID, speed, hater name, and message file to send SMS.

Commands:
/start - Start the bot
/help - Show this help message
/stop - Stop the SMS sending process
/status - Check your stats and active users

For approval or support, contact on WhatsApp:
📱 *""" + WHATSAPP_CONTACT + """*

The bot will continuously send messages in a loop until you send the /stop command.
"""
    await update.message.reply_text(help_text)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Check if user is approved
    if user_id not in user_approval_status or not user_approval_status[user_id]['approved']:
        await update.message.reply_text("You need to be approved to use this service. Use /start to begin the approval process.")
        return

    # Set stop flag for this specific user
    context.user_data['stop_sending'] = True

    # Kill the user's task if it exists
    if user_id in active_tasks:
        await update.message.reply_text('Stopping your SMS sending process. Please wait...')
    else:
        await update.message.reply_text('You don\'t have any active SMS sending process.')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    # Only approved users can see status
    if user_id not in user_approval_status or not user_approval_status[user_id]['approved']:
        await update.message.reply_text("You need to be approved to use this service. Use /start to begin the approval process.")
        return
    
    # Get current active users count
    active_users = sum(1 for uid, stats in user_stats.items() if stats['running'])
    
    # Get user's own stats
    user_messages = user_stats[user_id]['messages_sent']
    last_activity = user_stats[user_id]['last_activity'] or "Never"
    
    status_message = f"""
*Bot Status Report* 📊

*Your Stats:*
Messages Sent: {user_messages}
Last Activity: {last_activity}

*System Stats:*
Active Users: {active_users}/50
Total Approved Users: {len(user_approval_status)}

*Support:*
WhatsApp: *{WHATSAPP_CONTACT}*
    """
    
    await update.message.reply_text(status_message, parse_mode='Markdown')

async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the user's ID
    user_id = update.effective_user.id

    # Check if the message starts with /addkey
    if not update.message.text.startswith('/addkey '):
        await update.message.reply_text('Usage: /addkey <new_key>')
        return

    # Extract the new key from the message
    new_key = update.message.text.split(' ', 1)[1].strip()

    # Check if the key already exists
    if new_key in APPROVED_KEYS:
        await update.message.reply_text(f'The key \'{new_key}\' already exists!')
        return

    # Add the new key to the list
    APPROVED_KEYS.append(new_key)
    await update.message.reply_text(f'Key \'{new_key}\' added successfully!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Handle approval key verification
    if 'step' in context.user_data and context.user_data['step'] == 'waiting_for_approval':
        approval_key = update.message.text.strip()

        if approval_key in APPROVED_KEYS:
            user_approval_status[user_id] = {
                'approved': True,
                'key': approval_key
            }
            await update.message.reply_text('✅ Your key has been approved! You can now use the bot.')
            await update.message.reply_text('Please send your token.')
            context.user_data['step'] = 'waiting_for_token'
        else:
            await update.message.reply_text('❌ Invalid approval key. Please contact the admin on WhatsApp:')
            await update.message.reply_text(f'📱 {WHATSAPP_CONTACT}')
        return

    # Check if user is approved for all other steps
    if user_id not in user_approval_status or not user_approval_status[user_id]['approved']:
        await update.message.reply_text("You need to be approved to use this service. Use /start to begin the approval process.")
        return

    if 'step' not in context.user_data:
        context.user_data['step'] = 'waiting_for_token'

    if context.user_data['step'] == 'waiting_for_token':
        context.user_data['token'] = update.message.text
        await update.message.reply_text('Token received. Now please send your TID.')
        context.user_data['step'] = 'waiting_for_tid'

    elif context.user_data['step'] == 'waiting_for_tid':
        context.user_data['tid'] = update.message.text
        await update.message.reply_text('TID received. Now please send the speed (in seconds between messages).')
        context.user_data['step'] = 'waiting_for_speed'

    elif context.user_data['step'] == 'waiting_for_speed':
        context.user_data['speed'] = update.message.text
        await update.message.reply_text('Speed received. Now please send the hater\'s name.')
        context.user_data['step'] = 'waiting_for_hater_name'

    elif context.user_data['step'] == 'waiting_for_hater_name':
        context.user_data['hater_name'] = update.message.text
        await update.message.reply_text('Hater name received. Now please send the text file or paste your messages.')
        context.user_data['step'] = 'waiting_for_file_content'

    elif context.user_data['step'] == 'waiting_for_file_content':
        context.user_data['file_content'] = update.message.text
        username = update.effective_user.username or "User"
        current_time = datetime.now(pytz.timezone('Asia/Karachi')).strftime("%Y-%m-%d %I:%M:%S %p")
        
        start_message = f"""
*SMS Sending Started* ✅
*User:* {username}
*Time:* {current_time}
*TID:* {context.user_data['tid']}
*Speed:* {context.user_data['speed']} seconds

This will continue looping until you send /stop command.
For any issues, contact on WhatsApp: *{WHATSAPP_CONTACT}*
        """
        
        await update.message.reply_text(start_message, parse_mode='Markdown')

        # Reset the user-specific stop flag before starting
        context.user_data['stop_sending'] = False

        # Get the user's ID
        user_id = update.effective_user.id

        # Stop any existing task for this user
        if user_id in active_tasks:
            context.user_data['stop_sending'] = True
            # Small wait to ensure the task sees the stop signal
            await asyncio.sleep(0.5)

        # Start SMS sending in a separate task to avoid blocking the bot
        chat_id = update.effective_chat.id
        sms_task = asyncio.create_task(
            send_messages_from_file(
                context.user_data['token'],
                context.user_data['tid'],
                context.user_data['hater_name'],
                context.user_data['speed'],
                context.user_data['file_content'],
                chat_id,
                context,
                user_id
            )
        )

        # Store the task reference
        active_tasks[user_id] = sms_task

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Check if user is approved
    if user_id not in user_approval_status or not user_approval_status[user_id]['approved']:
        await update.message.reply_text("You need to be approved to use this service. Use /start to begin the approval process.")
        return

    if 'step' not in context.user_data or context.user_data['step'] != 'waiting_for_file_content':
        await update.message.reply_text('Please first send token, TID, speed, and hater name.')
        return

    file = await update.message.document.get_file()

    # Download the file and read its contents
    file_content = ""
    try:
        file_bytes = await file.download_as_bytearray()
        file_content = file_bytes.decode('utf-8')
    except Exception as e:
        await update.message.reply_text(f'Error reading file: {str(e)}')
        return

    await update.message.reply_text('File received. Starting to send SMS. This will continue looping until you send /stop command.')

    # Reset the user-specific stop flag before starting
    context.user_data['stop_sending'] = False

    # Get the user's ID
    user_id = update.effective_user.id

    # Stop any existing task for this user
    if user_id in active_tasks:
        context.user_data['stop_sending'] = True
        # Small wait to ensure the task sees the stop signal
        await asyncio.sleep(0.5)

    # Start SMS sending in a separate task to avoid blocking the bot
    chat_id = update.effective_chat.id
    sms_task = asyncio.create_task(
        send_messages_from_file(
            context.user_data['token'],
            context.user_data['tid'],
            context.user_data['hater_name'],
            context.user_data['speed'],
            file_content,
            chat_id,
            context,
            user_id
        )
    )

    # Store the task reference
    active_tasks[user_id] = sms_task

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors caused by updates."""
    print(f"Update caused error: {context.error}")
    if isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ An error occurred: {context.error}"
        )

def main() -> None:
    # Create the Application and pass the bot token
    builder = Application.builder()
    application = builder.token(TELEGRAM_BOT_TOKEN).build()

    # Start the server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("addkey", add_key))

    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    print("Bot started, press Ctrl+C to stop")
    
    # Configure more robust polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        pool_timeout=30,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30
    )

if __name__ == "__main__":
    main()
                    
