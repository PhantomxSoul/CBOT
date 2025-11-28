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

# Image & Links
START_IMG_URL = os.getenv("START_IMG_URL", "") 
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/YourSupportGroup")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/YourUpdateChannel")
OWNER_LINK = os.getenv("OWNER_LINK", "https://t.me/YourOwnerUsername")

# Logger Setup
try:
    LOGGER_ID = int(os.getenv("LOGGER_ID", "0").strip())
except:
    LOGGER_ID = 0

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
TAX_RATE = 0.10  # 10% Tax on transfers

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
    SUDO_USERS.clear()
    SUDO_USERS.add(OWNER_ID)
    if SUDO_IDS_STR:
        for x in SUDO_IDS_STR.split(","):
            if x.strip().isdigit(): SUDO_USERS.add(int(x.strip()))
    for doc in sudoers_collection.find({}):
        SUDO_USERS.add(doc["user_id"])

reload_sudoers()

def get_mention(user_data, custom_name=None):
    """Aesthetic clickable mention."""
    if hasattr(user_data, "id"): 
        name = custom_name or user_data.first_name
        name = html.escape(name)
        return f"<a href='tg://user?id={user_data.id}'><b>{name}</b></a>"
    elif isinstance(user_data, dict):
        name = custom_name or user_data.get("name", "User")
        name = html.escape(name)
        uid = user_data.get("user_id")
        return f"<a href='tg://user?id={uid}'><b>{name}</b></a>"
    return "Unknown"

def ensure_user_exists(tg_user):
    user_doc = users_collection.find_one({"user_id": tg_user.id})
    username = tg_user.username.lower() if tg_user.username else None

    if not user_doc:
        new_user = {
            "user_id": tg_user.id, "name": tg_user.first_name, "username": username,
            "balance": 0, "kills": 0, "status": "alive",
            "protection_expiry": datetime.utcnow(), "registered_at": datetime.utcnow(),
        }
        users_collection.insert_one(new_user)
        return new_user
    else:
        if user_doc.get("username") != username or user_doc.get("name") != tg_user.first_name:
            users_collection.update_one({"user_id": tg_user.id}, {"$set": {"username": username, "name": tg_user.first_name}})
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
                clean = arg.strip("@").lower()
                target_doc = users_collection.find_one({"username": clean})
                if not target_doc: return None, f"❌ <b>Baka!</b> Who is <code>@{clean}</code>?"
                return target_doc, None

            if arg.isdigit() and len(arg) > 6:
                target_id = int(arg)
                target_doc = users_collection.find_one({"user_id": target_id})
                if not target_doc: return None, f"❌ <b>Oops!</b> ID <code>{target_id}</code> not found."
                return target_doc, None
    return None, "No target"

def is_protected(user_data):
    if "protection_expiry" not in user_data: return False
    return user_data["protection_expiry"] > datetime.utcnow()

def format_money(amount):
    return f"${amount:,}"

def format_time(timedelta_obj):
    total_seconds = int(timedelta_obj.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours}h {minutes}m"

def make_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 𝐔𝐩𝐝𝐚𝐭𝐞𝐬", url=SUPPORT_CHANNEL), InlineKeyboardButton("💬 𝐒𝐮𝐩𝐩𝐨𝐫𝐭", url=SUPPORT_GROUP)],
        [InlineKeyboardButton("♛ 𝐎𝐰𝐧𝐞𝐫", url=OWNER_LINK)]
    ])

async def send_log(context, text):
    if LOGGER_ID != 0:
        try: await context.bot.send_message(chat_id=LOGGER_ID, text=text, parse_mode=ParseMode.HTML)
        except: pass

# ================== 🎮 USER COMMANDS ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user_exists(user)

    caption = (
        f"👋 <b>Kon'nichiwa</b> {get_mention(user)}! (⁠≧⁠▽⁠≦⁠)\n\n"
        f"『 <b>{BOT_NAME}</b> 』\n"
        f"<i>The cutest economy bot on Telegram!</i> 🌸\n\n"
        f"🎮 <b>𝐆𝐚𝐦𝐞 𝐌𝐞𝐧𝐮:</b>\n"
        f"<code>/kill</code> • <code>/rob</code> • <code>/give</code>\n"
        f"<code>/bal</code> • <code>/ranking</code>\n\n"
        f"💭 <b>𝐍𝐞𝐞𝐝 𝐇𝐞𝐥𝐩?</b>\n"
        f"Type <code>/help</code> for my secret diary!\n"
    )

    if START_IMG_URL and START_IMG_URL.startswith("http"):
        try: await update.message.reply_photo(photo=START_IMG_URL, caption=caption, parse_mode=ParseMode.HTML, reply_markup=make_main_keyboard())
        except: await update.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=make_main_keyboard())
    else:
        await update.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=make_main_keyboard())

    await send_log(context, f"🚀 <b>Bot Started</b>\n👤 {get_mention(user)} (`{user.id}`)\n📍 {update.effective_chat.title}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"📖 <b>{BOT_NAME} 𝐃𝐢𝐚𝐫𝐲</b> 🌸\n\n"
        f"👤 <b>𝐔𝐬𝐞𝐫 𝐙𝐨𝐧𝐞:</b>\n"
        f"✦ <code>/start</code> » Wake me up\n"
        f"✦ <code>/register</code> » Get bonus {format_money(REGISTER_BONUS)}\n"
        f"✦ <code>/bal</code> » Check pouch\n"
        f"✦ <code>/ranking</code> » Global top list\n"
        f"✦ <code>/give [amt]</code> » Transfer coins\n"
        f"✦ <code>/kill</code> » Attack user 🔪\n"
        f"✦ <code>/rob</code> » Steal coins 💰\n"
        f"✦ <code>/protect 1d</code> » Buy Shield 🛡️\n"
        f"✦ <code>/revive</code> » Revive life ✨\n\n"
        f"👮 <b>𝐀𝐝𝐦𝐢𝐧 𝐙𝐨𝐧𝐞:</b>\n"
        f"✦ <code>/sudo</code> » Secret Menu\n"
        f"✦ <code>/sudolist</code> » Staff List\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if get_user(user.id): return await update.message.reply_text(f"✨ <b>Ara?</b> {get_mention(user)}, you already claimed it!", parse_mode=ParseMode.HTML)

    new_user = {
        "user_id": user.id, "name": user.first_name, "username": user.username.lower() if user.username else None,
        "balance": REGISTER_BONUS, "kills": 0, "status": "alive", "protection_expiry": datetime.utcnow(), "registered_at": datetime.utcnow(),
    }
    users_collection.insert_one(new_user)
    await update.message.reply_text(f"🎉 <b>Yayy!</b> {get_mention(user)} Registered!\n🎁 Bonus: <b>+{format_money(REGISTER_BONUS)}</b>", parse_mode=ParseMode.HTML)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target, error = resolve_target(update, context)
    if not target and error == "No target": target = ensure_user_exists(update.effective_user)
    elif not target: return await update.message.reply_text(error, parse_mode=ParseMode.HTML)

    rank = users_collection.count_documents({"balance": {"$gt": target["balance"]}}) + 1
    status = "💖 Alive" if target['status'] == 'alive' else "💀 Dead"

    msg = (
        f"👤 <b>User:</b> {get_mention(target)}\n"
        f"👛 <b>Balance:</b> <code>{format_money(target['balance'])}</code>\n"
        f"🏆 <b>Rank:</b> <code>#{rank}</code>\n"
        f"❤️ <b>Status:</b> {status}\n"
        f"⚔️ <b>Kills:</b> <code>{target['kills']}</code>"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rich = users_collection.find().sort("balance", -1).limit(10)
    msg = "💎 <b>𝐓𝐨𝐩 𝟏𝟎 𝐑𝐢𝐜𝐡𝐢𝐞𝐬:</b>\n"
    for i, d in enumerate(rich, 1): msg += f"<code>{i}.</code> {get_mention(d)}: <b>{format_money(d['balance'])}</b>\n"

    kills = users_collection.find().sort("kills", -1).limit(10)
    msg += "\n🩸 <b>𝐓𝐨𝐩 𝟏𝟎 𝐊𝐢𝐥𝐥𝐞𝐫𝐬:</b>\n"
    for i, d in enumerate(kills, 1): msg += f"<code>{i}.</code> {get_mention(d)}: <b>{d['kills']} Kills</b>\n"

    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = ensure_user_exists(update.effective_user)
    args = context.args

    # Logic: /give <amount> <target> OR Reply + /give <amount>
    if not args: return await update.message.reply_text("⚠️ <b>Usage:</b> <code>/give 100 @user</code>", parse_mode=ParseMode.HTML)

    try: amount = int(args[0])
    except: return await update.message.reply_text("⚠️ <b>Baka!</b> Amount must be a number.", parse_mode=ParseMode.HTML)

    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "⚠️ Tag someone to give coins.", parse_mode=ParseMode.HTML)

    if amount <= 0: return await update.message.reply_text("⚠️ Don't be cheeky!", parse_mode=ParseMode.HTML)
    if sender['balance'] < amount: return await update.message.reply_text(f"📉 You only have <code>{format_money(sender['balance'])}</code>", parse_mode=ParseMode.HTML)
    if sender['user_id'] == target['user_id']: return await update.message.reply_text("🤔 Giving money to yourself?", parse_mode=ParseMode.HTML)

    # Tax Logic
    tax = int(amount * TAX_RATE)
    final_amt = amount - tax

    # DB Updates
    users_collection.update_one({"user_id": sender["user_id"]}, {"$inc": {"balance": -amount}})
    users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": final_amt}})

    # Send Tax to Owner (Ensure owner exists in DB first)
    owner_doc = users_collection.find_one({"user_id": OWNER_ID})
    if owner_doc:
        users_collection.update_one({"user_id": OWNER_ID}, {"$inc": {"balance": tax}})

    msg = (
        f"💸 <b>Transfer Complete!</b>\n"
        f"👤 <b>From:</b> {get_mention(sender)}\n"
        f"👤 <b>To:</b> {get_mention(target)}\n"
        f"💰 <b>Amount:</b> <code>{format_money(final_amt)}</code>\n"
        f"🏦 <b>Tax (10%):</b> <code>{format_money(tax)}</code> (Paid to Owner)"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    await send_log(context, f"🔄 <b>Coin Transfer</b>\n{get_mention(sender)} gave <code>{amount}</code> to {get_mention(target)}")

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user_exists(update.effective_user)
    if not context.args: return await update.message.reply_text(f"⚠️ <b>Usage:</b> <code>/protect 1d</code> or <code>2d</code>", parse_mode=ParseMode.HTML)

    dur = context.args[0].lower()
    if dur == '1d': cost, days = PROTECT_1D_COST, 1
    elif dur == '2d': cost, days = PROTECT_2D_COST, 2
    else: return await update.message.reply_text("⚠️ 1d or 2d only!", parse_mode=ParseMode.HTML)

    if is_protected(user): 
        rem = user['protection_expiry'] - datetime.utcnow()
        return await update.message.reply_text(f"🛡️ <b>Safe!</b> You have {format_time(rem)} left.", parse_mode=ParseMode.HTML)

    if user['balance'] < cost: return await update.message.reply_text(f"❌ Need <code>{format_money(cost)}</code>!", parse_mode=ParseMode.HTML)

    users_collection.update_one({"user_id": user["user_id"]}, {"$inc": {"balance": -cost}, "$set": {"protection_expiry": datetime.utcnow() + timedelta(days=days)}})
    await update.message.reply_text(f"🛡️ <b>Shield Activated!</b> Safe for {days} days.", parse_mode=ParseMode.HTML)

async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = ensure_user_exists(update.effective_user)
    target, _ = resolve_target(update, context)

    # If no target, revive self
    if not target or target['user_id'] == sender['user_id']:
        is_self = True
        target = sender
    else:
        is_self = False

    if target['status'] == 'alive': return await update.message.reply_text(f"✨ {get_mention(target)} is already alive!", parse_mode=ParseMode.HTML)

    if sender['balance'] < REVIVE_COST:
        return await update.message.reply_text(f"❌ You need <code>{format_money(REVIVE_COST)}</code> to revive {'yourself' if is_self else 'them'}.", parse_mode=ParseMode.HTML)

    users_collection.update_one({"user_id": sender["user_id"]}, {"$inc": {"balance": -REVIVE_COST}})
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "alive"}})

    if is_self:
        await update.message.reply_text(f"💖 <b>Revived!</b> Welcome back!", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"💖 <b>Hero!</b> You revived {get_mention(target)} for <code>{format_money(REVIVE_COST)}</code>!", parse_mode=ParseMode.HTML)

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error if error != "No target" else "⚠️ Reply to kill!", parse_mode=ParseMode.HTML)

    if attacker['status'] == 'dead': return await update.message.reply_text("💀 <b>You are dead!</b> /revive first.", parse_mode=ParseMode.HTML)
    if target['user_id'] == attacker['user_id']: return await update.message.reply_text("🤔 Don't do that.", parse_mode=ParseMode.HTML)
    if target['status'] == 'dead': return await update.message.reply_text("⚰️ Already dead.", parse_mode=ParseMode.HTML)

    if is_protected(target): 
        rem = target['protection_expiry'] - datetime.utcnow()
        return await update.message.reply_text(f"🛡️ <b>Blocked!</b> They are safe for <code>{format_time(rem)}</code>.", parse_mode=ParseMode.HTML)

    reward = random.randint(100, 200)
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "dead"}})
    users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"kills": 1, "balance": reward}})

    await update.message.reply_text(f"🔪 {get_mention(attacker)} <b>KILLED</b> {get_mention(target)}!\n💀 Status: <b>DEAD</b>\n💵 Loot: <b>{format_money(reward)}</b>", parse_mode=ParseMode.HTML)

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    if not context.args: return await update.message.reply_text("⚠️ <code>/rob 100 @user</code>", parse_mode=ParseMode.HTML)
    try: amount = int(context.args[0])
    except: return await update.message.reply_text("⚠️ Invalid amount.", parse_mode=ParseMode.HTML)

    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "⚠️ Tag a victim.", parse_mode=ParseMode.HTML)

    if attacker['status'] == 'dead': return await update.message.reply_text("💀 You are dead.", parse_mode=ParseMode.HTML)
    if target['user_id'] == attacker['user_id']: return await update.message.reply_text("🤦‍♂️ No.", parse_mode=ParseMode.HTML)
    if target['status'] == 'dead': return await update.message.reply_text("⚰️ Corpse has no money.", parse_mode=ParseMode.HTML)

    if is_protected(target):
        rem = target['protection_expiry'] - datetime.utcnow()
        return await update.message.reply_text(f"🛡️ <b>Shielded!</b> Safe for <code>{format_time(rem)}</code>.", parse_mode=ParseMode.HTML)

    if target['balance'] < amount: return await update.message.reply_text("📉 They are too poor.", parse_mode=ParseMode.HTML)

    if random.choice([True, False]):
        users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": -amount}})
        users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"balance": amount}})
        await update.message.reply_text(f"💰 {get_mention(attacker)} stole <b>{format_money(amount)}</b> from {get_mention(target)}!", parse_mode=ParseMode.HTML)
    else:
        fine = int(amount * 0.1)
        users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"balance": -fine}})
        await update.message.reply_text(f"🚔 <b>Police!</b> {get_mention(attacker)} caught! Paid <b>{format_money(fine)}</b> fine.", parse_mode=ParseMode.HTML)

# ================== 👑 SUDO/OWNER COMMANDS ==================

async def sudo_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    msg = (
        "🔐 <b>𝐒𝐮𝐝𝐨 𝐏𝐚𝐧𝐞𝐥</b>\n\n"
        "‣ <code>/addcoins [amt] [user]</code>\n"
        "‣ <code>/rmcoins [amt] [user]</code>\n"
        "‣ <code>/freerevive [user]</code>\n"
        "‣ <code>/sudolist</code>\n\n"
        "👑 <b>𝐎𝐰𝐧𝐞𝐫:</b>\n"
        "‣ <code>/addsudo [user]</code>\n"
        "‣ <code>/rmsudo [user]</code>\n"
        "‣ <code>/cleandb</code>\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def sudolist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "👑 <b>𝐎𝐰𝐧𝐞𝐫 & 𝐒𝐮𝐝𝐨𝐞𝐫𝐬:</b>\n\n"
    owner_doc = get_user(OWNER_ID)
    msg += f"👑 {get_mention(owner_doc) if owner_doc else f'<code>{OWNER_ID}</code>'} (Owner)\n"

    for uid in SUDO_USERS:
        if uid == OWNER_ID: continue
        u_doc = get_user(uid)
        msg += f"👮 {get_mention(u_doc) if u_doc else f'<code>{uid}</code>'}\n"
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

# --- Confirmation System ---

def get_confirm_keyboard(action, args_str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ 𝐘𝐞𝐬", callback_data=f"cnf|{action}|{args_str}"), InlineKeyboardButton("❌ 𝐍𝐨", callback_data="cnf|cancel|0")]])

async def ask_confirm(update: Update, text: str, action: str, args_str: str):
    await update.message.reply_text(f"⚠️ <b>Wait!</b> {text}\nAre you sure?", parse_mode=ParseMode.HTML, reply_markup=get_confirm_keyboard(action, args_str))

async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /addsudo <target>", parse_mode=ParseMode.HTML)
    if target['user_id'] in SUDO_USERS: return await update.message.reply_text("⚠️ Already Sudoer.", parse_mode=ParseMode.HTML)
    await ask_confirm(update, f"Promote {get_mention(target)}?", "addsudo", str(target['user_id']))

async def rmsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /rmsudo <target>", parse_mode=ParseMode.HTML)
    if target['user_id'] not in SUDO_USERS: return await update.message.reply_text("⚠️ Not a Sudoer.", parse_mode=ParseMode.HTML)
    await ask_confirm(update, f"Demote {get_mention(target)}?", "rmsudo", str(target['user_id']))

async def addcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    args = context.args
    if not args: return await update.message.reply_text("Usage: /addcoins <amt> <user>", parse_mode=ParseMode.HTML)
    try: amt = int(args[0])
    except: return await update.message.reply_text("Invalid amount.", parse_mode=ParseMode.HTML)
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "No target.", parse_mode=ParseMode.HTML)
    await ask_confirm(update, f"Give <b>{format_money(amt)}</b> to {get_mention(target)}?", "addcoins", f"{target['user_id']}|{amt}")

async def rmcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    args = context.args
    if not args: return await update.message.reply_text("Usage: /rmcoins <amt> <user>", parse_mode=ParseMode.HTML)
    try: amt = int(args[0])
    except: return await update.message.reply_text("Invalid amount.", parse_mode=ParseMode.HTML)
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "No target.", parse_mode=ParseMode.HTML)
    await ask_confirm(update, f"Remove <b>{format_money(amt)}</b> from {get_mention(target)}?", "rmcoins", f"{target['user_id']}|{amt}")

async def freerevive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    target, error = resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /freerevive <target>", parse_mode=ParseMode.HTML)
    await ask_confirm(update, f"Free Revive {get_mention(target)}?", "freerevive", str(target['user_id']))

async def cleandb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    await ask_confirm(update, "<b>WIPE DATABASE?</b> 🗑️", "cleandb", "0")

async def confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in SUDO_USERS: return await query.message.edit_text("❌ <b>Baka!</b> Not for you.", parse_mode=ParseMode.HTML)

    data = query.data.split("|")
    action = data[1]
    if action == "cancel": return await query.message.edit_text("❌ <b>Cancelled!</b>", parse_mode=ParseMode.HTML)

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
        amt = int(data[3])
        users_collection.update_one({"user_id": uid}, {"$inc": {"balance": amt}})
        await query.message.edit_text(f"✅ Added <b>{format_money(amt)}</b> to <code>{uid}</code>.", parse_mode=ParseMode.HTML)
    elif action == "rmcoins":
        uid = int(data[2])
        amt = int(data[3])
        users_collection.update_one({"user_id": uid}, {"$inc": {"balance": -amt}})
        await query.message.edit_text(f"✅ Removed <b>{format_money(amt)}</b> from <code>{uid}</code>.", parse_mode=ParseMode.HTML)
    elif action == "freerevive":
        uid = int(data[2])
        users_collection.update_one({"user_id": uid}, {"$set": {"status": "alive"}})
        await query.message.edit_text(f"✅ User <code>{uid}</code> revived for free!", parse_mode=ParseMode.HTML)
    elif action == "cleandb":
        users_collection.delete_many({})
        await query.message.edit_text("🗑️ <b>DATABASE WIPED!</b>", parse_mode=ParseMode.HTML)

# ================== 🕵️ LOGGING ==================

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.my_chat_member: return
    new = update.my_chat_member.new_chat_member
    chat = update.my_chat_member.chat
    user = update.my_chat_member.from_user

    if new.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        link = "No Link"
        if new.status == ChatMember.ADMINISTRATOR:
            try: link = await context.bot.export_chat_invite_link(chat.id)
            except: pass
        await send_log(context, f"🆕 <b>Bot Added!</b>\n📍 {chat.title}\n👤 By: {get_mention(user)}\n🔗 {link}")

    elif new.status in [ChatMember.LEFT, ChatMember.BANNED]:
        await send_log(context, f"❌ <b>Bot Removed/Left</b>\n📍 {chat.title}\n👤 By: {get_mention(user)}")

# ================== MAIN ==================

app = Flask(__name__)
@app.route('/')
def health(): return "Baka Bot Ultimate Alive"
def run_flask(): app.run(host='0.0.0.0', port=PORT)

async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Start game"), BotCommand("help", "Diary"),
        BotCommand("register", "Bonus"), BotCommand("bal", "Balance"),
        BotCommand("ranking", "Leaderboard"), BotCommand("give", "Transfer"),
        BotCommand("kill", "Attack"), BotCommand("rob", "Steal"),
        BotCommand("protect", "Shield"), BotCommand("revive", "Live again"),
    ]
    await application.bot.set_my_commands(commands)
    await send_log(application, f"🌟 <b>Baka Bot Restarted!</b>\nOnline and Ready! (⁠≧⁠▽⁠≦⁠)")

if __name__ == '__main__':
    Thread(target=run_flask).start()
    if not TOKEN: print("CRITICAL: BOT_TOKEN missing.")
    else:
        app_bot = ApplicationBuilder().token(TOKEN).build()
        app_bot.add_handler(CommandHandler("start", start))
        app_bot.add_handler(CommandHandler("help", help_command))
        app_bot.add_handler(CommandHandler("register", register))
        app_bot.add_handler(CommandHandler("bal", balance))
        app_bot.add_handler(CommandHandler("ranking", ranking))
        app_bot.add_handler(CommandHandler("give", give))
        app_bot.add_handler(CommandHandler("protect", protect))
        app_bot.add_handler(CommandHandler("revive", revive))
        app_bot.add_handler(CommandHandler("kill", kill))
        app_bot.add_handler(CommandHandler("rob", rob))

        app_bot.add_handler(CommandHandler("sudo", sudo_help))
        app_bot.add_handler(CommandHandler("sudolist", sudolist))
        app_bot.add_handler(CommandHandler("addsudo", addsudo))
        app_bot.add_handler(CommandHandler("rmsudo", rmsudo))
        app_bot.add_handler(CommandHandler("addcoins", addcoins))
        app_bot.add_handler(CommandHandler("rmcoins", rmcoins))
        app_bot.add_handler(CommandHandler("freerevive", freerevive))
        app_bot.add_handler(CommandHandler("cleandb", cleandb))
        app_bot.add_handler(CallbackQueryHandler(confirm_handler, pattern="^cnf\|"))
        app_bot.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

        app_bot.post_init = set_bot_commands
        print(f"Baka Bot Started on Port {PORT}...")
        app_bot.run_polling()