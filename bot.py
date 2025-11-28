import os
import logging
import random
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask


# Turn off the spammy "POST /getUpdates" logs
logging.getLogger("httpx").setLevel(logging.WARNING)

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
# We use .strip() and int() to ensure cleaner env var parsing
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
HEADER_ART = "◄❥͜͡⃟⃝💔꯭᪳𝄄─𝐃꯭𝐄꯭𝐀꯭𝐃<꯭/꯭᪵>𝐔꯭𝐒𝐄꯭𝐑─𝄄꯭➤⃝ ⃝⃪⃕☠️"
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
logger = logging.getLogger(__name__)

# ================== HELPER FUNCTIONS ==================

def get_user(user_id):
    """Fetch user from DB by Telegram ID."""
    return users_collection.find_one({"user_id": user_id})

def ensure_user_exists(tg_user):
    """
    Get user from DB, or create basic entry if not exists.
    Also updates the username if it changed.
    """
    user_doc = users_collection.find_one({"user_id": tg_user.id})
    
    current_username = tg_user.username.lower() if tg_user.username else None
    
    if not user_doc:
        new_user = {
            "user_id": tg_user.id,
            "name": tg_user.first_name,
            "username": current_username,
            "balance": 0, # No bonus on auto-create
            "kills": 0,
            "status": "alive",
            "protection_expiry": datetime.utcnow(),
            "registered_at": datetime.utcnow(),
        }
        users_collection.insert_one(new_user)
        return new_user
    else:
        # Update username if it's missing or changed (for @mention lookups)
        if user_doc.get("username") != current_username:
            users_collection.update_one(
                {"user_id": tg_user.id}, 
                {"$set": {"username": current_username}}
            )
        return user_doc

def resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Determines the target user based on:
    1. Reply to message
    2. Mention (@username) in args
    3. User ID in args
    Returns: (user_dict, error_message_string)
    """
    args = context.args
    target_doc = None

    # 1. Check Reply
    if update.message.reply_to_message:
        target_tg = update.message.reply_to_message.from_user
        # We assume if they are replying, the user "exists" in Telegram, 
        # but we need them in OUR db.
        target_doc = ensure_user_exists(target_tg)
        return target_doc, None

    # 2. Check Args (if exists)
    if args and len(args) > 0:
        query = args[0]
        
        # If input is @username
        if query.startswith("@"):
            clean_username = query.strip("@").lower()
            target_doc = users_collection.find_one({"username": clean_username})
            if not target_doc:
                return None, f"❌ Could not find user with username @{clean_username} in my database."
            return target_doc, None
            
        # If input is User ID (digits)
        if query.isdigit():
            target_id = int(query)
            target_doc = users_collection.find_one({"user_id": target_id})
            if not target_doc:
                # Try to see if it's the sender themselves? No, usually ID means target.
                return None, f"❌ Could not find User ID {target_id} in database."
            return target_doc, None

    # 3. No target found
    return None, "No target"

def is_protected(user_data):
    if "protection_expiry" not in user_data:
        return False
    return user_data["protection_expiry"] > datetime.utcnow()

def format_money(amount):
    return f"${amount:,}"

# ================== USER COMMANDS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user_exists(update.effective_user)
    msg = (
        f"{HEADER_ART}\n\n"
        f"✨ **Hey {update.effective_user.first_name}!**\n"
        f"Welcome to {BOT_NAME}.\n\n"
        f"📜 **Commands:**\n"
        f"/register - Get {format_money(REGISTER_BONUS)} bonus\n"
        f"/bal - Check balance (reply/mention to check others)\n"
        f"/kill - Kill a user (Random reward $100-$200)\n"
        f"/rob <amount> - Rob a user\n"
        f"/protect 1d - Buy protection\n"
        f"/revive - Revive yourself ($500)\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Check manual existence to give bonus ONLY if new
    existing = get_user(user_id)
    
    if existing:
        await update.message.reply_text(f"{BOT_NAME}: ✨ You are already registered!")
        return

    # Create new with bonus
    new_user = {
        "user_id": user_id,
        "name": update.effective_user.first_name,
        "username": update.effective_user.username.lower() if update.effective_user.username else None,
        "balance": REGISTER_BONUS,
        "kills": 0,
        "status": "alive",
        "protection_expiry": datetime.utcnow(),
        "registered_at": datetime.utcnow(),
    }
    users_collection.insert_one(new_user)
    await update.message.reply_text(f"{BOT_NAME}: 🎉 Registered! +{format_money(REGISTER_BONUS)} added.")

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Try to resolve a target (reply/mention/id)
    target_user, error = resolve_target(update, context)
    
    # If no target specified (args/reply), default to SELF
    if not target_user and error == "No target":
        target_user = ensure_user_exists(update.effective_user)
    elif not target_user:
        # If attempted to find target but failed (e.g. wrong ID)
        await update.message.reply_text(error)
        return

    # Calculate rank
    rank = users_collection.count_documents({"balance": {"$gt": target_user["balance"]}}) + 1
    
    msg = (
        f"{HEADER_ART}\n"
        f"👤 **Name:** {target_user['name']}\n"
        f"💰 **Balance:** {format_money(target_user['balance'])}\n"
        f"🏆 **Rank:** {rank}\n"
        f"❤️ **Status:** {target_user['status'].upper()}\n"
        f"⚔️ **Kills:** {target_user['kills']}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user_exists(update.effective_user)
    
    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/protect 1d` or `/protect 2d`", parse_mode="Markdown")
        return

    duration = context.args[0].lower()
    if duration == '1d':
        cost, days = PROTECT_1D_COST, 1
    elif duration == '2d':
        cost, days = PROTECT_2D_COST, 2
    else:
        await update.message.reply_text("⚠️ Invalid duration.")
        return

    if is_protected(user):
        await update.message.reply_text(f"{BOT_NAME}: 🛡️ You are already protected!")
        return

    if user['balance'] < cost:
        await update.message.reply_text(f"{BOT_NAME}: ❌ You need {format_money(cost)}!")
        return

    users_collection.update_one(
        {"user_id": user["user_id"]},
        {
            "$inc": {"balance": -cost},
            "$set": {"protection_expiry": datetime.utcnow() + timedelta(days=days)}
        }
    )
    await update.message.reply_text(f"{BOT_NAME}: 🛡️ Protected for {days} days.")

async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user_exists(update.effective_user)
    
    if user['status'] == 'alive':
        await update.message.reply_text(f"{BOT_NAME}: ✨ You are already alive!")
        return

    if user['balance'] < REVIVE_COST:
        await update.message.reply_text(f"{BOT_NAME}: ❌ You need {format_money(REVIVE_COST)} to revive.")
        return

    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"balance": -REVIVE_COST}, "$set": {"status": "alive"}}
    )
    await update.message.reply_text(f"{BOT_NAME}: ❤️ You revived yourself for {format_money(REVIVE_COST)}.")

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    
    target, error = resolve_target(update, context)
    if not target:
        await update.message.reply_text(error if error != "No target" else "⚠️ usage: /kill <reply/mention/id>")
        return

    if attacker['status'] == 'dead':
        await update.message.reply_text(f"{BOT_NAME}: 💀 You are dead! Revive first.")
        return

    if target['user_id'] == attacker['user_id']:
        await update.message.reply_text("🤔 Suicidal?")
        return

    if target['status'] == 'dead':
        await update.message.reply_text("⚰️ They are already dead.")
        return

    if is_protected(target):
        await update.message.reply_text("🛡️ They are protected!")
        return

    # LOGIC: Kill + Reward
    kill_reward = random.randint(100, 200)
    
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "dead"}})
    users_collection.update_one(
        {"user_id": attacker["user_id"]}, 
        {
            "$inc": {"kills": 1, "balance": kill_reward}
        }
    )

    await update.message.reply_text(
        f"{HEADER_ART}\n"
        f"🔪 You KILLED {target['name']}! 🩸\n"
        f"💀 Their status is now DEAD.\n"
        f"💵 You looted **{format_money(kill_reward)}** from their corpse!"
    , parse_mode="Markdown")

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    
    # We need to parse Amount AND Target
    # Patterns: 
    # 1. Reply + /rob <amount>
    # 2. /rob <amount> <mention/id>
    
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Usage: /rob <amount> <user>")
        return

    # Try to find amount first
    try:
        amount = int(args[0])
        # If targeting via text, the target is in args[1], so we remove args[0] for the resolver
        if len(args) > 1:
            context.args = args[1:] 
        else:
            context.args = [] # Rely on reply
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
        await update.message.reply_text("⚰️ Can't rob the dead.")
        return

    if is_protected(target):
        await update.message.reply_text("🛡️ Protected!")
        return

    if target['balance'] < amount:
        await update.message.reply_text(f"📉 They only have {format_money(target['balance'])}.")
        return

    # 50% chance
    if random.choice([True, False]):
        users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": -amount}})
        users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"balance": amount}})
        await update.message.reply_text(f"💰 You stole {format_money(amount)} from {target['name']}!")
    else:
        fine = int(amount * 0.1)
        users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"balance": -fine}})
        await update.message.reply_text(f"🚔 Police caught you! You paid {format_money(fine)} fine.")

# ================== SUDO COMMANDS ==================

async def addcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return

    # Args: <amount> <target> OR Reply + <amount>
    args = context.args
    if not args: return await update.message.reply_text("Usage: /addcoins <amount> <target>")

    try:
        amount = int(args[0])
        if len(args) > 1: context.args = args[1:] # Shift args for resolver
    except: return await update.message.reply_text("Invalid amount.")

    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "No target found.")

    users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": amount}})
    await update.message.reply_text(f"👑 Added {format_money(amount)} to {target['name']}.")

async def freerevive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sudo command to revive anyone for free.
    Usage: /freerevive @user OR reply
    """
    if update.effective_user.id not in SUDO_USERS: return
    
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /freerevive <target>")

    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "alive"}})
    await update.message.reply_text(f"👑 GOD MODE: {target['name']} has been revived for FREE! ✨")

async def userstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /userstats <target>")

    await update.message.reply_text(
        f"🔍 **Deep Stats:**\nID: `{target['user_id']}`\nName: {target['name']}\nStatus: {target['status']}\nBal: {target['balance']}\nProtected: {is_protected(target)}",
        parse_mode="Markdown"
    )

# ================== FAKE SERVER (RENDER) ==================

app = Flask(__name__)
@app.route('/')
def health(): return "Baka Bot Alive"
def run_flask(): app.run(host='0.0.0.0', port=PORT)

# ================== MAIN ==================

if __name__ == '__main__':
    # Start Web Server for Render
    Thread(target=run_flask).start()

    if not TOKEN:
        print("CRITICAL: BOT_TOKEN is missing.")
    else:
        app_bot = ApplicationBuilder().token(TOKEN).build()

        # Handlers
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CommandHandler("register", register))
        app_bot.add_handler(CommandHandler("bal", balance))
        app_bot.add_handler(CommandHandler("protect", protect))
        app_bot.add_handler(CommandHandler("revive", revive))
        app_bot.add_handler(CommandHandler("kill", kill))
        app_bot.add_handler(CommandHandler("rob", rob))

        # Sudo Handlers
        app_bot.add_handler(CommandHandler("addcoins", addcoins))
        app_bot.add_handler(CommandHandler("freerevive", freerevive))
        app_bot.add_handler(CommandHandler("userstats", userstats))

        print(f"Baka Bot Started on Port {PORT}...")
        app_bot.run_polling()