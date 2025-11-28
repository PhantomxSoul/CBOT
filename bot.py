import os
import logging
import random
import html
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

# Third-party imports
from telegram import (
    Update, 
    BotCommand, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ChatMember,
    ChatMemberUpdated
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
)
from pymongo import MongoClient
import certifi

# ================== 🌸 CONFIGURATION 🌸 ==================

TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
PORT = int(os.environ.get("PORT", 5000))

# Links
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/YourSupportGroup")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/YourUpdateChannel")
OWNER_LINK = os.getenv("OWNER_LINK", "https://t.me/YourOwnerUsername")

# Logging Channel (New!)
# Get this ID by forwarding a message from your channel to @userinfobot
try:
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0").strip())
except:
    LOG_CHANNEL_ID = 0

# Permissions
try:
    OWNER_ID = int(os.getenv("OWNER_ID", "0").strip())
except ValueError:
    OWNER_ID = 0

SUDO_IDS_STR = os.getenv("SUDO_IDS", "")
SUDO_USERS = set()

# Game Constants
BOT_NAME = "🫧 ʙᴀᴋᴀ ×͜࿐"
REVIVE_COST = 500
PROTECT_1D_COST = 1000
PROTECT_2D_COST = 1800
REGISTER_BONUS = 5000

# ================== 📦 DATABASE SETUP ==================

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["bakabot_db"]
users_collection = db["users"]
sudoers_collection = db["sudoers"]

# ================== 📠 LOGGING ==================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ================== 🛠️ HELPERS ==================

def reload_sudoers():
    """Refreshes the SUDO_USERS set."""
    SUDO_USERS.clear()
    SUDO_USERS.add(OWNER_ID)
    
    if SUDO_IDS_STR:
        for x in SUDO_IDS_STR.split(","):
            if x.strip().isdigit():
                SUDO_USERS.add(int(x.strip()))
    
    for doc in sudoers_collection.find({}):
        SUDO_USERS.add(doc["user_id"])

# Initial Load
reload_sudoers()

def get_mention(user_data):
    """Generates a Cute Markdown clickable mention."""
    if hasattr(user_data, "id"): 
        name = html.escape(user_data.first_name)
        return f"<a href='tg://user?id={user_data.id}'>{name}</a>"
    elif isinstance(user_data, dict):
        name = html.escape(user_data.get("name", "User"))
        uid = user_data.get("user_id")
        return f"<a href='tg://user?id={uid}'>{name}</a>"
    return "User"

def ensure_user_exists(tg_user):
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

    if update.message.reply_to_message:
        target_tg = update.message.reply_to_message.from_user
        target_doc = ensure_user_exists(target_tg)
        return target_doc, None

    if args and len(args) > 0:
        for arg in args:
            if arg.startswith("@"):
                clean_username = arg.strip("@").lower()
                target_doc = users_collection.find_one({"username": clean_username})
                if not target_doc:
                    return None, f"❌ <b>Oopsie!</b> Could not find user <code>@{clean_username}</code> in my diary."
                return target_doc, None
            
            if arg.isdigit() and len(arg) > 6:
                target_id = int(arg)
                target_doc = users_collection.find_one({"user_id": target_id})
                if not target_doc:
                    return None, f"❌ <b>Baka!</b> No user found with ID <code>{target_id}</code>."
                return target_doc, None

    return None, "No target"

def is_protected(user_data):
    if "protection_expiry" not in user_data:
        return False
    return user_data["protection_expiry"] > datetime.utcnow()

def format_money(amount):
    return f"${amount:,}"

def make_main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 𝐔𝐩𝐝𝐚𝐭𝐞𝐬", url=SUPPORT_CHANNEL),
            InlineKeyboardButton("🌸 𝐒𝐮𝐩𝐩𝐨𝐫𝐭", url=SUPPORT_GROUP),
        ],
        [
            InlineKeyboardButton("👑 𝐎𝐰𝐧𝐞𝐫", url=OWNER_LINK),
        ]
    ])

async def send_log(context: ContextTypes.DEFAULT_TYPE, text: str):
    """Sends logs to the configured channel."""
    if LOG_CHANNEL_ID != 0:
        try:
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Failed to log: {e}")

# ================== 🎮 USER COMMANDS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user_exists(user)
    
    msg = (
        f"👋 <b>Hiii</b> {get_mention(user)}! (⁠≧⁠▽⁠≦⁠)\n\n"
        f"✨ <b>Welcome to {BOT_NAME}!</b> ✨\n"
        f"<i>I am a sassy, cute economy bot!</i> 🌸\n\n"
        f"🎮 <b>Game Mode:</b>\n"
        f"<code>/kill</code> • <code>/rob</code> • <code>/bal</code>\n\n"
        f"📚 <b>Info:</b>\n"
        f"Type <code>/help</code> for my diary!\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=make_main_keyboard())

    # Log Start Usage
    log_text = (
        f"🚀 <b>Bot Started By User</b>\n"
        f"👤 <b>User:</b> {get_mention(user)}\n"
        f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        f"💬 <b>Chat:</b> {update.effective_chat.title} (`{update.effective_chat.id}`)"
    )
    await send_log(context, log_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"📚 <b>{BOT_NAME} Diary</b> 🌸\n\n"
        f"👤 <b>User Commands:</b>\n"
        f"✦ <code>/start</code> - Wake me up!\n"
        f"✦ <code>/register</code> - Get {format_money(REGISTER_BONUS)} (One Time)\n"
        f"✦ <code>/bal</code> - Check your pouch\n"
        f"✦ <code>/ranking</code> - Who is the best?\n"
        f"✦ <code>/kill</code> - Attack someone 🔪\n"
        f"✦ <code>/rob</code> - Steal coins 💰\n"
        f"✦ <code>/protect 1d</code> - Buy Shield 🛡️\n"
        f"✦ <code>/revive</code> - Come back to life ✨\n\n"
        f"👑 <b>Admin Stuff:</b>\n"
        f"✦ <code>/sudo</code> - Secret commands\n"
        f"✦ <code>/sudolist</code> - My Bosses\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = get_user(user.id)
    if existing:
        return await update.message.reply_text(f"✨ <b>Baka!</b> {get_mention(user)}, you are already registered! (⁠｡⁠•̀⁠ᴗ⁠-⁠)⁠✧", parse_mode=ParseMode.HTML)

    new_user = {
        "user_id": user.id, "name": user.first_name,
        "username": user.username.lower() if user.username else None,
        "balance": REGISTER_BONUS, "kills": 0, "status": "alive",
        "protection_expiry": datetime.utcnow(), "registered_at": datetime.utcnow(),
    }
    users_collection.insert_one(new_user)
    await update.message.reply_text(f"🎉 <b>Yay!</b> {get_mention(user)} Registered!\n💰 Here is your <b>+{format_money(REGISTER_BONUS)}</b> bonus!", parse_mode=ParseMode.HTML)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user, error = resolve_target(update, context)
    
    if not target_user and error == "No target":
        target_user = ensure_user_exists(update.effective_user)
    elif not target_user:
        return await update.message.reply_text(error, parse_mode=ParseMode.HTML)

    rank = users_collection.count_documents({"balance": {"$gt": target_user["balance"]}}) + 1
    status_emoji = "💖 Alive" if target_user['status'] == 'alive' else "💀 Dead"
    
    msg = (
        f"👤 <b>User:</b> {get_mention(target_user)}\n"
        f"👛 <b>Balance:</b> <code>{format_money(target_user['balance'])}</code>\n"
        f"🏆 <b>Rank:</b> <code>#{rank}</code>\n"
        f"❤️ <b>Status:</b> {status_emoji}\n"
        f"⚔️ <b>Kills:</b> <code>{target_user['kills']}</code>"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor_rich = users_collection.find().sort("balance", -1).limit(10)
    rich_text = "💰 <b>Top 10 Richies:</b>\n"
    for i, doc in enumerate(cursor_rich, 1):
        rich_text += f"<code>{i}.</code> {get_mention(doc)}: <b>{format_money(doc['balance'])}</b>\n"

    cursor_kills = users_collection.find().sort("kills", -1).limit(10)
    kill_text = "\n⚔️ <b>Top 10 Killers:</b>\n"
    for i, doc in enumerate(cursor_kills, 1):
        kill_text += f"<code>{i}.</code> {get_mention(doc)}: <b>{doc['kills']} Kills</b>\n"

    await update.message.reply_text(rich_text + kill_text, parse_mode=ParseMode.HTML)

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_doc = ensure_user_exists(update.effective_user)
    if not context.args:
        return await update.message.reply_text(f"⚠️ <b>Usage:</b> <code>/protect 1d</code> or <code>/protect 2d</code>", parse_mode=ParseMode.HTML)

    duration = context.args[0].lower()
    if duration == '1d': cost, days = PROTECT_1D_COST, 1
    elif duration == '2d': cost, days = PROTECT_2D_COST, 2
    else: return await update.message.reply_text("⚠️ <b>Invalid duration!</b> Try 1d or 2d.", parse_mode=ParseMode.HTML)

    if is_protected(user_doc): return await update.message.reply_text(f"🛡️ <b>Huh?</b> You are already protected! (⁠◡⁠ ⁠ω⁠ ⁠◡⁠)", parse_mode=ParseMode.HTML)
    if user_doc['balance'] < cost: return await update.message.reply_text(f"❌ <b>Poor!</b> You need <code>{format_money(cost)}</code>!", parse_mode=ParseMode.HTML)

    users_collection.update_one({"user_id": user_doc["user_id"]}, {"$inc": {"balance": -cost}, "$set": {"protection_expiry": datetime.utcnow() + timedelta(days=days)}})
    await update.message.reply_text(f"🛡️ <b>Shield Up!</b> You are safe for {days} days.", parse_mode=ParseMode.HTML)

async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_doc = ensure_user_exists(update.effective_user)
    if user_doc['status'] == 'alive': return await update.message.reply_text(f"✨ <b>Baka!</b> You are alive! (⁠｡⁠•̀⁠ᴗ⁠-⁠)⁠✧", parse_mode=ParseMode.HTML)
    if user_doc['balance'] < REVIVE_COST: return await update.message.reply_text(f"❌ <b>Sad!</b> You need <code>{format_money(REVIVE_COST)}</code> to revive.", parse_mode=ParseMode.HTML)

    users_collection.update_one({"user_id": user_doc["user_id"]}, {"$inc": {"balance": -REVIVE_COST}, "$set": {"status": "alive"}})
    await update.message.reply_text(f"💖 <b>Revived!</b> Welcome back to life!", parse_mode=ParseMode.HTML)

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error if error != "No target" else "⚠️ <b>Reply</b> or <b>Tag</b> someone to kill!", parse_mode=ParseMode.HTML)

    if attacker['status'] == 'dead': return await update.message.reply_text(f"💀 <b>You are dead!</b> /revive first.", parse_mode=ParseMode.HTML)
    if target['user_id'] == attacker['user_id']: return await update.message.reply_text("🤔 <b>Baka!</b> Don't kill yourself.", parse_mode=ParseMode.HTML)
    if target['status'] == 'dead': return await update.message.reply_text(f"⚰️ {get_mention(target)} is already dead.", parse_mode=ParseMode.HTML)
    if is_protected(target): return await update.message.reply_text(f"🛡️ {get_mention(target)} has a shield! Run!", parse_mode=ParseMode.HTML)

    kill_reward = random.randint(100, 200)
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "dead"}})
    users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"kills": 1, "balance": kill_reward}})

    await update.message.reply_text(
        f"🔪 {get_mention(attacker)} <b>KILLED</b> {get_mention(target)}! 🩸\n"
        f"💀 They are now <b>DEAD</b>.\n"
        f"💵 Looted: <b>{format_money(kill_reward)}</b>"
    , parse_mode=ParseMode.HTML)

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    args = context.args
    if not args: return await update.message.reply_text("⚠️ <b>Usage:</b> <code>/rob 100 @user</code>", parse_mode=ParseMode.HTML)

    try: amount = int(args[0])
    except ValueError: return await update.message.reply_text("⚠️ First argument must be number.", parse_mode=ParseMode.HTML)
    if amount <= 0: return await update.message.reply_text("⚠️ Invalid amount.", parse_mode=ParseMode.HTML)

    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error if error != "No target" else "⚠️ Provide a target.", parse_mode=ParseMode.HTML)

    if attacker['status'] == 'dead': return await update.message.reply_text("💀 You are dead.", parse_mode=ParseMode.HTML)
    if target['user_id'] == attacker['user_id']: return await update.message.reply_text("🤦‍♂️ No self-robbing.", parse_mode=ParseMode.HTML)
    if target['status'] == 'dead': return await update.message.reply_text(f"⚰️ {get_mention(target)} is dead.", parse_mode=ParseMode.HTML)
    if is_protected(target): return await update.message.reply_text(f"🛡️ {get_mention(target)} is safe!", parse_mode=ParseMode.HTML)
    if target['balance'] < amount: return await update.message.reply_text(f"📉 They are too poor.", parse_mode=ParseMode.HTML)

    if random.choice([True, False]):
        users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": -amount}})
        users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"balance": amount}})
        await update.message.reply_text(f"💰 {get_mention(attacker)} stole <b>{format_money(amount)}</b> from {get_mention(target)}!", parse_mode=ParseMode.HTML)
    else:
        fine = int(amount * 0.1)
        users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"balance": -fine}})
        await update.message.reply_text(f"🚔 <b>Police!</b> {get_mention(attacker)} caught! Paid <b>{format_money(fine)}</b> fine.", parse_mode=ParseMode.HTML)

# ================== 👑 SUDO/OWNER COMMANDS WITH CONFIRMATION ==================

async def sudo_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    msg = (
        "🔐 <b>Sudo Panel</b>\n\n"
        "<code>/addcoins [amt] [user]</code>\n"
        "<code>/freerevive [user]</code>\n"
        "<code>/sudolist</code>\n\n"
        "👑 <b>Owner:</b>\n"
        "<code>/addsudo [user]</code>\n"
        "<code>/rmsudo [user]</code>\n"
        "<code>/cleandb</code>\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def sudolist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "👑 <b>Owner & Sudoers:</b>\n\n"
    owner_doc = get_user(OWNER_ID)
    msg += f"👑 {get_mention(owner_doc) if owner_doc else OWNER_ID} (Owner)\n"
    
    for uid in SUDO_USERS:
        if uid == OWNER_ID: continue
        u_doc = get_user(uid)
        msg += f"👮 {get_mention(u_doc) if u_doc else uid}\n"
        
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# --- Confirmation System ---

def get_confirm_keyboard(action, args_str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"cnf|{action}|{args_str}"),
            InlineKeyboardButton("❌ No", callback_data="cnf|cancel|0")
        ]
    ])

async def ask_confirm(update: Update, text: str, action: str, args_str: str):
    await update.message.reply_text(
        f"⚠️ <b>Wait!</b> {text}\nAre you sure?", 
        parse_mode=ParseMode.HTML, 
        reply_markup=get_confirm_keyboard(action, args_str)
    )

# --- Commands triggering confirmation ---

async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /addsudo <target>", parse_mode=ParseMode.HTML)
    if target['user_id'] in SUDO_USERS: return await update.message.reply_text("⚠️ Already a Sudoer.", parse_mode=ParseMode.HTML)

    await ask_confirm(update, f"Promote {get_mention(target)} to Sudoer?", "addsudo", str(target['user_id']))

async def rmsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /rmsudo <target>", parse_mode=ParseMode.HTML)
    if target['user_id'] not in SUDO_USERS: return await update.message.reply_text("⚠️ Not a Sudoer.", parse_mode=ParseMode.HTML)

    await ask_confirm(update, f"Demote {get_mention(target)}?", "rmsudo", str(target['user_id']))

async def addcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    args = context.args
    if not args: return await update.message.reply_text("Usage: /addcoins <amount> <target>", parse_mode=ParseMode.HTML)
    try: amount = int(args[0])
    except: return await update.message.reply_text("Invalid amount.", parse_mode=ParseMode.HTML)
    
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "No target found.", parse_mode=ParseMode.HTML)

    await ask_confirm(update, f"Give <b>{format_money(amount)}</b> to {get_mention(target)}?", "addcoins", f"{target['user_id']}|{amount}")

async def freerevive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /freerevive <target>", parse_mode=ParseMode.HTML)

    await ask_confirm(update, f"Free Revive {get_mention(target)}?", "freerevive", str(target['user_id']))

async def cleandb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await ask_confirm(update, "<b>WIPE ENTIRE DATABASE?</b> 🗑️\nThis cannot be undone!", "cleandb", "0")

# --- Callback Handler ---

async def confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in SUDO_USERS:
        return await query.message.edit_text("❌ <b>Baka!</b> Not for you.", parse_mode=ParseMode.HTML)

    data = query.data.split("|")
    action = data[1]
    
    if action == "cancel":
        return await query.message.edit_text("❌ <b>Cancelled!</b> (⁠｡⁠•̀⁠ᴗ⁠-⁠)⁠✧", parse_mode=ParseMode.HTML)

    # Process Action
    if action == "addsudo":
        uid = int(data[2])
        sudoers_collection.insert_one({"user_id": uid})
        reload_sudoers()
        await query.message.edit_text(f"✅ User <code>{uid}</code> is now <b>Sudoer!</b>", parse_mode=ParseMode.HTML)

    elif action == "rmsudo":
        uid = int(data[2])
        sudoers_collection.delete_one({"user_id": uid})
        reload_sudoers()
        await query.message.edit_text(f"🗑️ User <code>{uid}</code> demoted.", parse_mode=ParseMode.HTML)

    elif action == "addcoins":
        uid = int(data[2])
        amount = int(data[3])
        users_collection.update_one({"user_id": uid}, {"$inc": {"balance": amount}})
        await query.message.edit_text(f"✅ Added <b>{format_money(amount)}</b> to <code>{uid}</code>.", parse_mode=ParseMode.HTML)

    elif action == "freerevive":
        uid = int(data[2])
        users_collection.update_one({"user_id": uid}, {"$set": {"status": "alive"}})
        await query.message.edit_text(f"✅ User <code>{uid}</code> revived for free!", parse_mode=ParseMode.HTML)

    elif action == "cleandb":
        users_collection.delete_many({})
        await query.message.edit_text("🗑️ <b>DATABASE WIPED!</b> All gone.", parse_mode=ParseMode.HTML)

# ================== 🕵️ LOGGING HANDLER ==================

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.my_chat_member: return
    
    new_member = update.my_chat_member.new_chat_member
    chat = update.my_chat_member.chat
    user = update.my_chat_member.from_user
    
    # Check if Bot was added
    if new_member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        invite_link = "No Link (Not Admin)"
        
        # Try to get invite link if admin
        if new_member.status == ChatMember.ADMINISTRATOR:
            try:
                link_obj = await context.bot.export_chat_invite_link(chat.id)
                invite_link = link_obj
            except: pass

        log_text = (
            f"🆕 <b>Bot Added to Group!</b>\n"
            f"📍 <b>Group:</b> {chat.title} (`{chat.id}`)\n"
            f"👤 <b>Added By:</b> {get_mention(user)} (`{user.id}`)\n"
            f"🔗 <b>Link:</b> {invite_link}"
        )
        await send_log(context, log_text)

# ================== MAIN ==================

app = Flask(__name__)
@app.route('/')
def health(): return "Baka Bot Cute Mode Alive"
def run_flask(): app.run(host='0.0.0.0', port=PORT)

async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Start game"),
        BotCommand("help", "Help Diary"),
        BotCommand("register", "Bonus"),
        BotCommand("bal", "Balance"),
        BotCommand("ranking", "Leaderboard"),
        BotCommand("kill", "Attack"),
        BotCommand("rob", "Steal"),
        BotCommand("protect", "Shield"),
        BotCommand("revive", "Live again"),
    ]
    await application.bot.set_my_commands(commands)
    
    # Startup Log
    if LOG_CHANNEL_ID != 0:
        try:
            await application.bot.send_message(
                LOG_CHANNEL_ID, 
                f"🌟 <b>Baka Bot Started!</b>\nI am online and cute! (⁠≧⁠▽⁠≦⁠)", 
                parse_mode=ParseMode.HTML
            )
        except: pass

if __name__ == '__main__':
    Thread(target=run_flask).start()
    if not TOKEN:
        print("CRITICAL: BOT_TOKEN is missing.")
    else:
        app_bot = ApplicationBuilder().token(TOKEN).build()
        
        # Handlers
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CommandHandler("help", help_command))
        app_bot.add_handler(CommandHandler("register", register))
        app_bot.add_handler(CommandHandler("bal", balance))
        app_bot.add_handler(CommandHandler("ranking", ranking))
        app_bot.add_handler(CommandHandler("protect", protect))
        app_bot.add_handler(CommandHandler("revive", revive))
        app_bot.add_handler(CommandHandler("kill", kill))
        app_bot.add_handler(CommandHandler("rob", rob))

        # Admin & Confirmation
        app_bot.add_handler(CommandHandler("sudo", sudo_help))
        app_bot.add_handler(CommandHandler("sudolist", sudolist))
        app_bot.add_handler(CommandHandler("addsudo", addsudo))
        app_bot.add_handler(CommandHandler("rmsudo", rmsudo))
        app_bot.add_handler(CommandHandler("addcoins", addcoins))
        app_bot.add_handler(CommandHandler("freerevive", freerevive))
        app_bot.add_handler(CommandHandler("cleandb", cleandb))
        app_bot.add_handler(CallbackQueryHandler(confirm_handler, pattern="^cnf\|"))

        # Logging Handler
        app_bot.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

        async def on_startup(app):
            await set_bot_commands(app)
        app_bot.post_init = on_startup

        print(f"Baka Bot Started on Port {PORT}...")
        app_bot.run_polling()