import os
import logging
import random
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
)
from pymongo import MongoClient
import certifi

# ================== CONFIG ==================

TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Owner id (int) and sudo user ids (comma separated) from env
OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # set on Heroku
SUDO_IDS = os.getenv("SUDO_IDS", "")        # e.g. "12345,67890"
SUDO_USERS = {int(x.strip()) for x in SUDO_IDS.split(",") if x.strip().isdigit()}

SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/YourSupportGroup")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/YourUpdateChannel")
OWNER_BUTTON_LINK = os.getenv("OWNER_LINK", "https://t.me/YourOwnerUsername")

BOT_NAME = "🫧 ʙᴀᴋᴀ ×͜࿐"
REVIVE_COST = 500
PROTECT_1D_COST = 1000
PROTECT_2D_COST = 1800
REGISTER_BONUS = 5000

# ================ DB SETUP ==================

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["bakabot_db"]
users_collection = db["users"]

# ================ LOGGING ===================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

# ============== HELPERS =====================

def get_user(user_id):
    return users_collection.find_one({"user_id": user_id})

def create_user(user_id, first_name):
    if get_user(user_id):
        return False
    new_user = {
        "user_id": user_id,
        "name": first_name,
        "balance": REGISTER_BONUS,
        "kills": 0,
        "status": "alive",
        "protection_expiry": datetime.utcnow(),
        "registered_at": datetime.utcnow(),
    }
    users_collection.insert_one(new_user)
    return True

def ensure_user_exists(user_id, first_name):
    """Auto-create a minimal user without bonus if not registered yet."""
    user = get_user(user_id)
    if user:
        return user
    # No auto bonus, just basic profile
    new_user = {
        "user_id": user_id,
        "name": first_name,
        "balance": 0,
        "kills": 0,
        "status": "alive",
        "protection_expiry": datetime.utcnow(),
        "registered_at": datetime.utcnow(),
    }
    users_collection.insert_one(new_user)
    return new_user

def is_protected(user_data):
    if "protection_expiry" not in user_data:
        return False
    return user_data["protection_expiry"] > datetime.utcnow()

def format_money(amount):
    return f"{amount:,}"

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_sudo(user_id: int) -> bool:
    return user_id in SUDO_USERS or is_owner(user_id)

# ============== UI PIECES ===================

def make_main_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📢 Updates", url=SUPPORT_CHANNEL),
                InlineKeyboardButton("👥 Support", url=SUPPORT_GROUP),
            ],
            [
                InlineKeyboardButton("👑 Owner", url=OWNER_BUTTON_LINK),
            ],
        ]
    )

# ============== COMMANDS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    first = user.first_name

    text = (
        f"✨ Hey {first}, welcome to {BOT_NAME}!\n\n"
        "💸 Fun coin game with kill / rob / protect / revive features.\n"
        "🎁 Use /register if you want a one-time free bonus.\n\n"
        "📚 Use /help to see all commands and details."
    )

    await update.message.reply_text(
        text,
        reply_markup=make_main_keyboard(),
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📚 ᴮᵃᵏᵃ ᴴᵉˡᵖ ᴹᵉⁿᵘ\n\n"
        "👤 User Commands:\n"
        "-  /start - Show welcome message & buttons\n"
        "-  /help - Show this help\n"
        "-  /register - Optional, get free 5,000 coins once\n"
        "-  /bal - Check your stats & rank\n"
        "-  /protect 1d|2d - Buy shield\n"
        "-  /revive - Revive if dead\n"
        "-  /kill (reply) - Kill a user\n"
        "-  /rob <amount> (reply) - Rob coins from a user\n\n"
        "👑 Owner / Sudo Commands:\n"
        "-  /addcoins <id> <amount>\n"
        "-  /removecoins <id> <amount>\n"
        "-  /setcoins <id> <amount>\n"
        "-  /userstats <id> - Check any user stats\n"
    )
    await update.message.reply_text(text, reply_markup=make_main_keyboard())

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    success = create_user(user.id, user.first_name)

    if success:
        msg = (
            f"🎉 {user.first_name}, registration successful!\n"
            f"💰 You got +{format_money(REGISTER_BONUS)} coins as bonus."
        )
    else:
        msg = "✨ You are already registered and bonus was already claimed."
    await update.message.reply_text(msg)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user_data = ensure_user_exists(tg_user.id, tg_user.first_name)

    rank = users_collection.count_documents(
        {"balance": {"$gt": user_data["balance"]}}
    ) + 1

    msg = (
        f"👤 Name: {user_data['name']}\n"
        f"💰 Balance: {format_money(user_data['balance'])}\n"
        f"🏆 Global Rank: {rank}\n"
        f"❤️ Status: {user_data['status']}\n"
        f"⚔️ Kills: {user_data['kills']}"
    )
    await update.message.reply_text(msg)

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user_data = ensure_user_exists(tg_user.id, tg_user.first_name)

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /protect 1d or /protect 2d")
        return

    duration = context.args.lower()
    if duration == "1d":
        cost = PROTECT_1D_COST
        time_add = timedelta(days=1)
    elif duration == "2d":
        cost = PROTECT_2D_COST
        time_add = timedelta(days=2)
    else:
        await update.message.reply_text("⚠️ Invalid duration. Use 1d or 2d.")
        return

    if is_protected(user_data):
        await update.message.reply_text("🛡️ You are already protected right now.")
        return

    if user_data["balance"] < cost:
        await update.message.reply_text(
            f"❌ You need {format_money(cost)} coins to buy this shield."
        )
        return

    new_expiry = datetime.utcnow() + time_add
    users_collection.update_one(
        {"user_id": user_data["user_id"]},
        {"$inc": {"balance": -cost}, "$set": {"protection_expiry": new_expiry}},
    )

    await update.message.reply_text(
        f"🛡️ Shield activated for {duration}! -{format_money(cost)} coins."
    )

async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user_data = ensure_user_exists(tg_user.id, tg_user.first_name)

    if user_data["status"] == "alive":
        await update.message.reply_text("✨ You are already alive.")
        return

    if user_data["balance"] < REVIVE_COST:
        await update.message.reply_text(
            f"❌ You need {format_money(REVIVE_COST)} coins to revive."
        )
        return

    users_collection.update_one(
        {"user_id": user_data["user_id"]},
        {"$inc": {"balance": -REVIVE_COST}, "$set": {"status": "alive"}},
    )

    await update.message.reply_text(
        f"❤️ You revived yourself! -{format_money(REVIVE_COST)} coins."
    )

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to the user you want to kill with /kill.")
        return

    attacker_tg = update.effective_user
    target_msg = update.message.reply_to_message
    target_tg = target_msg.from_user

    attacker = ensure_user_exists(attacker_tg.id, attacker_tg.first_name)
    target = ensure_user_exists(target_tg.id, target_tg.first_name)

    if attacker["status"] == "dead":
        await update.message.reply_text("💀 You are dead. Use /revive first.")
        return

    if target["user_id"] == attacker["user_id"]:
        await update.message.reply_text("🤔 Why are you trying to kill yourself?")
        return

    if target["status"] == "dead":
        await update.message.reply_text("⚰️ They are already dead.")
        return

    if is_protected(target):
        await update.message.reply_text("🛡️ Target is protected, kill failed.")
        return

    users_collection.update_one(
        {"user_id": target["user_id"]},
        {"$set": {"status": "dead"}},
    )
    users_collection.update_one(
        {"user_id": attacker["user_id"]},
        {"$inc": {"kills": 1}},
    )

    await update.message.reply_text(
        f"🔪 {attacker_tg.first_name} killed {target_tg.first_name}! 🩸"
    )

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ Reply to the user you want to rob with /rob <amount>."
        )
        return

    robber_tg = update.effective_user
    target_msg = update.message.reply_to_message
    target_tg = target_msg.from_user

    robber = ensure_user_exists(robber_tg.id, robber_tg.first_name)
    target = ensure_user_exists(target_tg.id, target_tg.first_name)

    if robber["status"] == "dead":
        await update.message.reply_text("💀 You are dead. You can’t rob anyone.")
        return

    try:
        amount = int(context.args)
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /rob <amount> (replying to a user)")
        return

    if amount <= 0:
        await update.message.reply_text("⚠️ Amount must be positive.")
        return

    if target["user_id"] == robber["user_id"]:
        await update.message.reply_text("😑 You can’t rob yourself.")
        return

    if target["status"] == "dead":
        await update.message.reply_text("⚰️ You can’t rob dead users.")
        return

    if is_protected(target):
        await update.message.reply_text("🛡️ They are protected. Rob failed.")
        return

    if target["balance"] < amount:
        await update.message.reply_text("📉 They don’t have that many coins.")
        return

    # 50-50 chance
    if random.choice([True, False]):
        users_collection.update_one(
            {"user_id": target["user_id"]},
            {"$inc": {"balance": -amount}},
        )
        users_collection.update_one(
            {"user_id": robber["user_id"]},
            {"$inc": {"balance": amount}},
        )
        await update.message.reply_text(
            f"💰 Success! You stole {format_money(amount)} coins from {target_tg.first_name}."
        )
    else:
        fine = max(1, int(amount * 0.1))
        users_collection.update_one(
            {"user_id": robber["user_id"]},
            {"$inc": {"balance": -fine}},
        )
        await update.message.reply_text(
            f"🚔 Police caught you! You paid {format_money(fine)} coins as a bribe."
        )

# ============ OWNER / SUDO COMMANDS =================

async def addcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addcoins <user_id> <amount>")
        return
    try:
        uid = int(context.args)
        amount = int(context.args)[1]
    except ValueError:
        await update.message.reply_text("Invalid arguments.")
        return

    user = ensure_user_exists(uid, str(uid))
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"balance": amount}},
    )
    await update.message.reply_text(
        f"👑 Added {format_money(amount)} coins to {user['name']} ({uid})."
    )

async def removecoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /removecoins <user_id> <amount>")
        return
    try:
        uid = int(context.args)
        amount = int(context.args)[1]
    except ValueError:
        await update.message.reply_text("Invalid arguments.")
        return

    user = ensure_user_exists(uid, str(uid))
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"balance": -amount}},
    )
    await update.message.reply_text(
        f"👑 Removed {format_money(amount)} coins from {user['name']} ({uid})."
    )

async def setcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setcoins <user_id> <amount>")
        return
    try:
        uid = int(context.args)
        amount = int(context.args)[1]
    except ValueError:
        await update.message.reply_text("Invalid arguments.")
        return

    user = ensure_user_exists(uid, str(uid))
    users_collection.update_one(
        {"user_id": user["user_id"]},
        {"$set": {"balance": amount}},
    )
    await update.message.reply_text(
        f"👑 Set {user['name']} ({uid}) coins to {format_money(amount)}."
    )

async def userstats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_sudo(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /userstats <user_id>")
        return
    try:
        uid = int(context.args)
    except ValueError:
        await update.message.reply_text("Invalid user_id.")
        return

    user = get_user(uid)
    if not user:
        await update.message.reply_text("User not found in DB.")
        return

    rank = users_collection.count_documents(
        {"balance": {"$gt": user["balance"]}}
    ) + 1

    msg = (
        f"👤 ID: {uid}\n"
        f"👤 Name: {user.get('name', 'Unknown')}\n"
        f"💰 Balance: {format_money(user['balance'])}\n"
        f"🏆 Rank: {rank}\n"
        f"❤️ Status: {user['status']}\n"
        f"⚔️ Kills: {user['kills']}"
    )
    await update.message.reply_text(msg)

# ============== FALLBACK ====================

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Use /help to see commands.")

# ============== MAIN ========================

async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help menu"),
        BotCommand("register", "Register and get bonus coins"),
        BotCommand("bal", "Check your balance & stats"),
        BotCommand("protect", "Buy shield 1d/2d"),
        BotCommand("revive", "Revive if you are dead"),
        BotCommand("kill", "Kill a user (reply)"),
        BotCommand("rob", "Rob coins (reply + amount)"),
    ]
    await application.bot.set_my_commands(commands)

def main():
    if not TOKEN:
        print("Error: BOT_TOKEN not found.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Normal commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("bal", balance))
    application.add_handler(CommandHandler("protect", protect))
    application.add_handler(CommandHandler("revive", revive))
    application.add_handler(CommandHandler("kill", kill))
    application.add_handler(CommandHandler("rob", rob))

    # Owner/Sudo commands
    application.add_handler(CommandHandler("addcoins", addcoins))
    application.add_handler(CommandHandler("removecoins", removecoins))
    application.add_handler(CommandHandler("setcoins", setcoins))
    application.add_handler(CommandHandler("userstats", userstats))

    # Unknown
    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    async def on_startup(app):
        await set_bot_commands(app)

    application.post_init = on_startup

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
    
