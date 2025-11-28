import os
import logging
import random
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

# Third-party imports
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from pymongo import MongoClient
import certifi

# ================== CONFIGURATION ==================

TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
PORT = int(os.environ.get("PORT", 5000))

# Permissions
try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0").strip())
except ValueError:
    OWNER_ID = 0

SUDO_IDS_STR = os.getenv("SUDO_IDS", "")
SUDO_USERS = set()
if SUDO_IDS_STR:
    for x in SUDO_IDS_STR.split(","):
        if x.strip().isdigit():
            SUDO_USERS.add(int(x.strip()))
SUDO_USERS.add(OWNER_ID)

# Game Constants
BOT_NAME = "🫧 ʙᴀᴋᴀ ×͜࿐"
REVIVE_COST = 500
PROTECT_1D_COST = 1000
PROTECT_2D_COST = 1800
REGISTER_BONUS = 5000

# ================== DATABASE SETUP ==================

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["bakabot_db"]
users_collection = db["users"]

# ================== LOGGING ==================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ================== HELPER FUNCTIONS ==================

def get_mention(user_data):
    """Generates a Markdown clickable mention."""
    # Handle Telegram User Object
    if hasattr(user_data, "id"): 
        name = user_data.first_name.replace("[", "").replace("]", "") # Sanitize
        return f"[{name}](tg://user?id={user_data.id})"
    # Handle Dictionary from DB
    elif isinstance(user_data, dict):
        name = user_data.get("name", "User").replace("[", "").replace("]", "")
        uid = user_data.get("user_id")
        return f"[{name}](tg://user?id={uid})"
    return "User"

def ensure_user_exists(tg_user):
    """Get user from DB, or create basic entry if not exists."""
    user_doc = users_collection.find_one({"user_id": tg_user.id})
    current_username = tg_user.username.lower() if tg_user.username else None
    
    if not user_doc:
        new_user = {
            "user_id": tg_user.id,
            "name": tg_user.first_name,
            "username": current_username,
            "balance": 0, 
            "kills": 0,
            "status": "alive",
            "protection_expiry": datetime.utcnow(),
            "registered_at": datetime.utcnow(),
        }
        users_collection.insert_one(new_user)
        return new_user
    else:
        # Update username if changed
        if user_doc.get("username") != current_username:
            users_collection.update_one(
                {"user_id": tg_user.id}, 
                {"$set": {"username": current_username}}
            )
        return user_doc

def get_user(user_id):
    return users_collection.find_one({"user_id": user_id})

def resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    target_doc = None

    # 1. Check Reply
    if update.message.reply_to_message:
        target_tg = update.message.reply_to_message.from_user
        target_doc = ensure_user_exists(target_tg)
        return target_doc, None

    # 2. Check Args (if exists)
    if args and len(args) > 0:
        for arg in args:
            if arg.startswith("@"):
                clean_username = arg.strip("@").lower()
                target_doc = users_collection.find_one({"username": clean_username})
                if not target_doc:
                    return None, f"❌ Could not find user @{clean_username} in DB."
                return target_doc, None
            
            if arg.isdigit() and len(arg) > 6:
                target_id = int(arg)
                target_doc = users_collection.find_one({"user_id": target_id})
                if not target_doc:
                    return None, f"❌ Could not find User ID {target_id}."
                return target_doc, None

    return None, "No target"

def is_protected(user_data):
    if "protection_expiry" not in user_data:
        return False
    return user_data["protection_expiry"] > datetime.utcnow()

def format_money(amount):
    return f"${amount:,}"

# ================== USER COMMANDS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user_exists(user)
    
    msg = (
        f"👋 {get_mention(user)}\n\n"
        f"✨ **Welcome to {BOT_NAME}!**\n\n"
        f"📜 **Commands:**\n"
        f"/register - Get {format_money(REGISTER_BONUS)} bonus\n"
        f"/bal - Check balance\n"
        f"/kill - Kill a user\n"
        f"/rob <amount> - Rob a user\n"
        f"/ranking - Global Top 10\n"
        f"/protect 1d - Buy protection\n"
        f"/revive - Revive yourself\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = get_user(user.id)
    
    if existing:
        await update.message.reply_text(f"✨ {get_mention(user)}, you are already registered!", parse_mode="Markdown")
        return

    new_user = {
        "user_id": user.id,
        "name": user.first_name,
        "username": user.username.lower() if user.username else None,
        "balance": REGISTER_BONUS,
        "kills": 0,
        "status": "alive",
        "protection_expiry": datetime.utcnow(),
        "registered_at": datetime.utcnow(),
    }
    users_collection.insert_one(new_user)
    await update.message.reply_text(f"🎉 {get_mention(user)} Registered! +{format_money(REGISTER_BONUS)} added.", parse_mode="Markdown")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user, error = resolve_target(update, context)
    
    if not target_user and error == "No target":
        target_user = ensure_user_exists(update.effective_user)
    elif not target_user:
        await update.message.reply_text(error)
        return

    rank = users_collection.count_documents({"balance": {"$gt": target_user["balance"]}}) + 1
    
    msg = (
        f"👤 **User:** {get_mention(target_user)}\n"
        f"💰 **Balance:** {format_money(target_user['balance'])}\n"
        f"🏆 **Rank:** {rank}\n"
        f"❤️ **Status:** {target_user['status'].upper()}\n"
        f"⚔️ **Kills:** {target_user['kills']}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Top 10 Richest
    cursor_rich = users_collection.find().sort("balance", -1).limit(10)
    rich_text = "💰 **Top 10 Richest:**\n"
    for i, doc in enumerate(cursor_rich, 1):
        rich_text += f"`{i}.` {get_mention(doc)}: **{format_money(doc['balance'])}**\n"

    # Top 10 Killers
    cursor_kills = users_collection.find().sort("kills", -1).limit(10)
    kill_text = "\n⚔️ **Top 10 Killers:**\n"
    for i, doc in enumerate(cursor_kills, 1):
        kill_text += f"`{i}.` {get_mention(doc)}: **{doc['kills']} Kills**\n"

    await update.message.reply_text(rich_text + kill_text, parse_mode="Markdown")

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_doc = ensure_user_exists(update.effective_user)
    
    if not context.args:
        await update.message.reply_text(f"⚠️ {get_mention(user_doc)} Usage: `/protect 1d` or `/protect 2d`", parse_mode="Markdown")
        return

    duration = context.args[0].lower()
    if duration == '1d':
        cost, days = PROTECT_1D_COST, 1
    elif duration == '2d':
        cost, days = PROTECT_2D_COST, 2
    else:
        await update.message.reply_text("⚠️ Invalid duration.")
        return

    if is_protected(user_doc):
        await update.message.reply_text(f"🛡️ {get_mention(user_doc)} is already protected!", parse_mode="Markdown")
        return

    if user_doc['balance'] < cost:
        await update.message.reply_text(f"❌ {get_mention(user_doc)} needs {format_money(cost)}!", parse_mode="Markdown")
        return

    users_collection.update_one(
        {"user_id": user_doc["user_id"]},
        {
            "$inc": {"balance": -cost},
            "$set": {"protection_expiry": datetime.utcnow() + timedelta(days=days)}
        }
    )
    await update.message.reply_text(f"🛡️ {get_mention(user_doc)} protected for {days} days.", parse_mode="Markdown")

async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_doc = ensure_user_exists(update.effective_user)
    
    if user_doc['status'] == 'alive':
        await update.message.reply_text(f"✨ {get_mention(user_doc)} is already alive!", parse_mode="Markdown")
        return

    if user_doc['balance'] < REVIVE_COST:
        await update.message.reply_text(f"❌ {get_mention(user_doc)} needs {format_money(REVIVE_COST)} to revive.", parse_mode="Markdown")
        return

    users_collection.update_one(
        {"user_id": user_doc["user_id"]},
        {"$inc": {"balance": -REVIVE_COST}, "$set": {"status": "alive"}}
    )
    await update.message.reply_text(f"❤️ {get_mention(user_doc)} revived for {format_money(REVIVE_COST)}.", parse_mode="Markdown")

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    
    target, error = resolve_target(update, context)
    if not target:
        await update.message.reply_text(error if error != "No target" else "⚠️ Reply or tag someone to kill.")
        return

    if attacker['status'] == 'dead':
        await update.message.reply_text(f"💀 {get_mention(attacker)} is dead! Revive first.", parse_mode="Markdown")
        return

    if target['user_id'] == attacker['user_id']:
        await update.message.reply_text("🤔 Suicidal?")
        return

    if target['status'] == 'dead':
        await update.message.reply_text(f"⚰️ {get_mention(target)} is already dead.", parse_mode="Markdown")
        return

    if is_protected(target):
        await update.message.reply_text(f"🛡️ {get_mention(target)} is protected!", parse_mode="Markdown")
        return

    kill_reward = random.randint(100, 200)
    
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "dead"}})
    users_collection.update_one(
        {"user_id": attacker["user_id"]}, 
        {
            "$inc": {"kills": 1, "balance": kill_reward}
        }
    )

    await update.message.reply_text(
        f"🔪 {get_mention(attacker)} KILLED {get_mention(target)}! 🩸\n"
        f"💀 {target['name']} is now DEAD.\n"
        f"💵 Looted: **{format_money(kill_reward)}**"
    , parse_mode="Markdown")

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Usage: /rob <amount> <user>")
        return

    try:
        amount = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ First argument must be amount.")
        return

    if amount <= 0:
        await update.message.reply_text("⚠️ Invalid amount.")
        return

    target, error = resolve_target(update, context)
    if not target:
        await update.message.reply_text(error if error != "No target" else "⚠️ Provide a target to rob.")
        return

    if attacker['status'] == 'dead':
        await update.message.reply_text("💀 You are dead.")
        return

    if target['user_id'] == attacker['user_id']:
        await update.message.reply_text("🤦‍♂️ Robbing yourself?")
        return
    
    if target['status'] == 'dead':
        await update.message.reply_text(f"⚰️ {get_mention(target)} is dead.", parse_mode="Markdown")
        return

    if is_protected(target):
        await update.message.reply_text(f"🛡️ {get_mention(target)} is protected!", parse_mode="Markdown")
        return

    if target['balance'] < amount:
        await update.message.reply_text(f"📉 They only have {format_money(target['balance'])}.")
        return

    if random.choice([True, False]):
        users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": -amount}})
        users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"balance": amount}})
        await update.message.reply_text(f"💰 {get_mention(attacker)} stole {format_money(amount)} from {get_mention(target)}!", parse_mode="Markdown")
    else:
        fine = int(amount * 0.1)
        users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"balance": -fine}})
        await update.message.reply_text(f"🚔 Police caught {get_mention(attacker)}! Paid {format_money(fine)} fine.", parse_mode="Markdown")

# ================== SUDO COMMANDS ==================

async def addcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    args = context.args
    if not args: return await update.message.reply_text("Usage: /addcoins <amount> <target>")
    try:
        amount = int(args[0])
    except: return await update.message.reply_text("Invalid amount.")

    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "No target found.")

    users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": amount}})
    await update.message.reply_text(f"👑 Added {format_money(amount)} to {get_mention(target)}.", parse_mode="Markdown")

async def freerevive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /freerevive <target>")

    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "alive"}})
    await update.message.reply_text(f"👑 GOD MODE: {get_mention(target)} has been revived for FREE! ✨", parse_mode="Markdown")

async def cleandb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """OWNER ONLY: Wipes the entire database."""
    if update.effective_user.id != OWNER_ID: return
    
    users_collection.delete_many({})
    await update.message.reply_text("🗑️ **DATABASE WIPED**\nAll users have been deleted.", parse_mode="Markdown")

# ================== BOT MENU SETUP ==================

async def set_bot_commands(application):
    """
    Sets the commands that appear when you type / in the chat.
    Does NOT include Sudo/Owner commands.
    """
    commands = [
        BotCommand("start", "Start the game"),
        BotCommand("register", "Get bonus coins"),
        BotCommand("bal", "Check balance & status"),
        BotCommand("ranking", "Global Leaderboard 🏆"),
        BotCommand("kill", "Kill a user"),
        BotCommand("rob", "Rob a user"),
        BotCommand("protect", "Buy protection"),
        BotCommand("revive", "Revive yourself"),
    ]
    await application.bot.set_my_commands(commands)

# ================== MAIN ==================

app = Flask(__name__)
@app.route('/')
def health(): return "Baka Bot Alive"
def run_flask(): app.run(host='0.0.0.0', port=PORT)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    if not TOKEN:
        print("CRITICAL: BOT_TOKEN is missing.")
    else:
        app_bot = ApplicationBuilder().token(TOKEN).build()
        
        # User Commands
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CommandHandler("register", register))
        app_bot.add_handler(CommandHandler("bal", balance))
        app_bot.add_handler(CommandHandler("ranking", ranking))
        app_bot.add_handler(CommandHandler("protect", protect))
        app_bot.add_handler(CommandHandler("revive", revive))
        app_bot.add_handler(CommandHandler("kill", kill))
        app_bot.add_handler(CommandHandler("rob", rob))

        # Sudo/Owner Commands
        app_bot.add_handler(CommandHandler("addcoins", addcoins))
        app_bot.add_handler(CommandHandler("freerevive", freerevive))
        app_bot.add_handler(CommandHandler("cleandb", cleandb))

        # Initialize Bot Commands Menu
        async def on_startup(app):
            await set_bot_commands(app)
        app_bot.post_init = on_startup

        print(f"Baka Bot Started on Port {PORT}...")
        app_bot.run_polling()