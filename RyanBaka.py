import os
import logging
import random
import html
import asyncio
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
    Chat
)
from telegram.constants import ParseMode, ChatType
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
)
from telegram.error import Forbidden, BadRequest
from pymongo import MongoClient
import certifi

# ================== 🌸 𝐂𝐎𝐍𝐅𝐈𝐆𝐔𝐑𝐀𝐓𝐈𝐎𝐍 🌸 ==================

TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
PORT = int(os.environ.get("PORT", 5000))

# Image & Links
START_IMG_URL = os.getenv("START_IMG_URL", "") 
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/YourSupportGroup")
SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/YourUpdateChannel")
OWNER_LINK = os.getenv("OWNER_LINK", "https://t.me/YourOwnerUsername")

# Logger Setup
try: LOGGER_ID = int(os.getenv("LOGGER_ID", "0").strip())
except: LOGGER_ID = 0

# Permissions
try: OWNER_ID = int(os.getenv("OWNER_ID", "0").strip())
except: OWNER_ID = 0

SUDO_IDS_STR = os.getenv("SUDO_IDS", "")
SUDO_USERS = set()

# Game Constants
BOT_NAME = "🫧 ʙᴀᴋᴀ ×͜࿐"
REVIVE_COST = 500
PROTECT_1D_COST = 1000
PROTECT_2D_COST = 1800
REGISTER_BONUS = 5000
TAX_RATE = 0.10

# ================== 📦 𝐃𝐀𝐓𝐀𝐁𝐀𝐒𝐄 📦 ==================

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["bakabot_db"]
users_collection = db["users"]
groups_collection = db["groups"] # New collection for broadcasts
sudoers_collection = db["sudoers"]

# ================== 📠 𝐋𝐎𝐆𝐆𝐈𝐍𝐆 ==================

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ================== 🛠️ 𝐇𝐄𝐋𝐏𝐄𝐑𝐒 ==================

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
    if hasattr(user_data, "id"): 
        name = custom_name or user_data.first_name
        return f"<a href='tg://user?id={user_data.id}'><b>{html.escape(name)}</b></a>"
    elif isinstance(user_data, dict):
        name = custom_name or user_data.get("name", "User")
        uid = user_data.get("user_id")
        return f"<a href='tg://user?id={uid}'><b>{html.escape(name)}</b></a>"
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
        # Update info if changed
        if user_doc.get("username") != username or user_doc.get("name") != tg_user.first_name:
            users_collection.update_one({"user_id": tg_user.id}, {"$set": {"username": username, "name": tg_user.first_name}})
        return user_doc

def track_group(chat):
    """Saves group ID for broadcasts"""
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if not groups_collection.find_one({"chat_id": chat.id}):
            groups_collection.insert_one({"chat_id": chat.id, "title": chat.title})

def get_user_from_db(user_id):
    return users_collection.find_one({"user_id": user_id})

async def resolve_target(update: Update, context: ContextTypes.DEFAULT_TYPE, specific_arg: str = None):
    """
    Smart resolver. 
    1. Checks Reply.
    2. Checks specific_arg (if provided, e.g. args[1]).
    3. Checks args[0] if specific_arg is None.
    """
    # 1. Reply
    if update.message.reply_to_message:
        target_tg = update.message.reply_to_message.from_user
        return ensure_user_exists(target_tg), None

    # 2. Text Argument
    query = specific_arg if specific_arg else (context.args[0] if context.args else None)
    
    if query:
        # User ID
        if query.isdigit():
            doc = users_collection.find_one({"user_id": int(query)})
            if doc: return doc, None
            return None, f"❌ <b>Baka!</b> ID <code>{query}</code> not found in database."
        
        # Username
        if query.startswith("@"):
            clean = query.strip("@").lower()
            doc = users_collection.find_one({"username": clean})
            if doc: return doc, None
            return None, f"❌ <b>Oops!</b> User <code>@{clean}</code> has not registered yet."

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

# ================== 🎮 𝐔𝐒𝐄𝐑 𝐂𝐎𝐌𝐌𝐀𝐍𝐃𝐒 ==================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    ensure_user_exists(user)
    track_group(chat)
    
    caption = (
        f"👋 <b>Kon'nichiwa</b> {get_mention(user)}! (⁠≧⁠▽⁠≦⁠)\n\n"
        f"『 <b>{BOT_NAME}</b> 』\n"
        f"<i>The aesthetic economy bot!</i> 🌸\n\n"
        f"🎮 <b>𝐆𝐚𝐦𝐞 𝐌𝐞𝐧𝐮:</b>\n"
        f"<code>/kill</code> • <code>/rob</code> • <code>/give</code>\n"
        f"<code>/bal</code> • <code>/ranking</code>\n\n"
        f"💭 <b>𝐍𝐞𝐞𝐝 𝐇𝐞𝐥𝐩?</b>\n"
        f"Type <code>/help</code> for details!\n"
    )

    if START_IMG_URL and START_IMG_URL.startswith("http"):
        try: await update.message.reply_photo(photo=START_IMG_URL, caption=caption, parse_mode=ParseMode.HTML, reply_markup=make_main_keyboard())
        except: await update.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=make_main_keyboard())
    else:
        await update.message.reply_text(caption, parse_mode=ParseMode.HTML, reply_markup=make_main_keyboard())

    if chat.type == ChatType.PRIVATE:
        await send_log(context, f"🚀 <b>Bot Started</b>\n👤 {get_mention(user)} (`{user.id}`)")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"📖 <b>{BOT_NAME} 𝐃𝐢𝐚𝐫𝐲</b> 🌸\n\n"
        f"👤 <b>𝐔𝐬𝐞𝐫 𝐙𝐨𝐧𝐞:</b>\n"
        f"✦ <code>/start</code> ➪ Wake me up\n"
        f"✦ <code>/register</code> ➪ Get {format_money(REGISTER_BONUS)}\n"
        f"✦ <code>/bal</code> ➪ Check wallet\n"
        f"✦ <code>/ranking</code> ➪ Global Tops\n"
        f"✦ <code>/give [amt] [user]</code> ➪ Transfer\n"
        f"✦ <code>/kill [user]</code> ➪ Attack 🔪\n"
        f"✦ <code>/rob [amt] [user]</code> ➪ Steal 💰\n"
        f"✦ <code>/protect 1d</code> ➪ Buy Shield\n"
        f"✦ <code>/revive [user]</code> ➪ Revive ✨\n\n"
        f"👮 <b>𝐀𝐝𝐦𝐢𝐧 𝐙𝐨𝐧𝐞:</b>\n"
        f"✦ <code>/sudo</code> ➪ Admin Panel\n"
        f"✦ <code>/sudolist</code> ➪ Staff\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if get_user_from_db(user.id): return await update.message.reply_text(f"✨ <b>Ara?</b> {get_mention(user)}, already registered!", parse_mode=ParseMode.HTML)

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
    
    # Needs amount + target
    if not args: return await update.message.reply_text("⚠️ <b>Usage:</b> <code>/give 100 @user</code>", parse_mode=ParseMode.HTML)

    try: amount = int(args[0])
    except: return await update.message.reply_text("⚠️ <b>Baka!</b> Amount must be a number.", parse_mode=ParseMode.HTML)

    # Use args[1] if present, else reply
    target_arg = args[1] if len(args) > 1 else None
    target, error = await resolve_target(update, context, specific_arg=target_arg)
    
    if not target: return await update.message.reply_text(error or "⚠️ Tag someone.", parse_mode=ParseMode.HTML)

    if amount <= 0: return await update.message.reply_text("⚠️ Don't be cheeky!", parse_mode=ParseMode.HTML)
    if sender['balance'] < amount: return await update.message.reply_text(f"📉 You only have <code>{format_money(sender['balance'])}</code>", parse_mode=ParseMode.HTML)
    if sender['user_id'] == target['user_id']: return await update.message.reply_text("🤔 To yourself?", parse_mode=ParseMode.HTML)

    tax = int(amount * TAX_RATE)
    final_amt = amount - tax

    users_collection.update_one({"user_id": sender["user_id"]}, {"$inc": {"balance": -amount}})
    users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": final_amt}})
    
    owner_doc = users_collection.find_one({"user_id": OWNER_ID})
    if owner_doc: users_collection.update_one({"user_id": OWNER_ID}, {"$inc": {"balance": tax}})

    msg = (
        f"💸 <b>Transfer Complete!</b>\n"
        f"👤 <b>From:</b> {get_mention(sender)}\n"
        f"👤 <b>To:</b> {get_mention(target)}\n"
        f"💰 <b>Sent:</b> <code>{format_money(final_amt)}</code>\n"
        f"🏦 <b>Tax:</b> <code>{format_money(tax)}</code>"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    await send_log(context, f"🔄 <b>Coin Transfer</b>\n{get_mention(sender)} gave <code>{amount}</code> to {get_mention(target)}")

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = ensure_user_exists(update.effective_user)
    if not context.args: return await update.message.reply_text(f"⚠️ <b>Usage:</b> <code>/protect 1d</code>", parse_mode=ParseMode.HTML)

    dur = context.args[0].lower()
    if dur == '1d': cost, days = PROTECT_1D_COST, 1
    elif dur == '2d': cost, days = PROTECT_2D_COST, 2
    else: return await update.message.reply_text("⚠️ 1d or 2d only!", parse_mode=ParseMode.HTML)

    if is_protected(user): 
        rem = user['protection_expiry'] - datetime.utcnow()
        return await update.message.reply_text(f"🛡️ <b>Safe!</b> You have {format_time(rem)} left.", parse_mode=ParseMode.HTML)
    
    if user['balance'] < cost: return await update.message.reply_text(f"❌ Need <code>{format_money(cost)}</code>!", parse_mode=ParseMode.HTML)

    users_collection.update_one({"user_id": user["user_id"]}, {"$inc": {"balance": -cost}, "$set": {"protection_expiry": datetime.utcnow() + timedelta(days=days)}})
    await update.message.reply_text(f"🛡️ <b>Shield Active!</b> Safe for {days} days.", parse_mode=ParseMode.HTML)

async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reviver = ensure_user_exists(update.effective_user)
    
    # Check if target provided
    target, _ = await resolve_target(update, context)
    
    # If no target provided, revive self
    if not target:
        target = reviver
        is_self = True
    else:
        is_self = target['user_id'] == reviver['user_id']

    if target['status'] == 'alive': return await update.message.reply_text(f"✨ {get_mention(target)} is already alive!", parse_mode=ParseMode.HTML)
    
    if reviver['balance'] < REVIVE_COST:
        return await update.message.reply_text(f"❌ You need <code>{format_money(REVIVE_COST)}</code>!", parse_mode=ParseMode.HTML)

    users_collection.update_one({"user_id": reviver["user_id"]}, {"$inc": {"balance": -REVIVE_COST}})
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "alive"}})
    
    if is_self:
        await update.message.reply_text(f"💖 <b>Revived!</b> Welcome back!", parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(f"💖 <b>Hero!</b> You paid <code>{format_money(REVIVE_COST)}</code> to revive {get_mention(target)}!", parse_mode=ParseMode.HTML)

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    target, error = await resolve_target(update, context)
    if not target: return await update.message.reply_text(error if error != "No target" else "⚠️ Reply or tag to kill!", parse_mode=ParseMode.HTML)

    if attacker['status'] == 'dead': return await update.message.reply_text("💀 <b>You are dead!</b> /revive first.", parse_mode=ParseMode.HTML)
    if target['user_id'] == attacker['user_id']: return await update.message.reply_text("🤔 Don't do that.", parse_mode=ParseMode.HTML)
    if target['status'] == 'dead': return await update.message.reply_text("⚰️ Already dead.", parse_mode=ParseMode.HTML)
    
    if is_protected(target): 
        rem = target['protection_expiry'] - datetime.utcnow()
        return await update.message.reply_text(f"🛡️ <b>Blocked!</b> Protected for <code>{format_time(rem)}</code>.", parse_mode=ParseMode.HTML)

    reward = random.randint(100, 200)
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "dead"}})
    users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"kills": 1, "balance": reward}})

    await update.message.reply_text(f"🔪 {get_mention(attacker)} <b>KILLED</b> {get_mention(target)}!\n💀 Status: <b>DEAD</b>\n💵 Loot: <b>{format_money(reward)}</b>", parse_mode=ParseMode.HTML)

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = ensure_user_exists(update.effective_user)
    if not context.args: return await update.message.reply_text("⚠️ <code>/rob 100 @user</code>", parse_mode=ParseMode.HTML)
    try: amount = int(context.args[0])
    except: return await update.message.reply_text("⚠️ Invalid amount.", parse_mode=ParseMode.HTML)

    target_arg = context.args[1] if len(context.args) > 1 else None
    target, error = await resolve_target(update, context, specific_arg=target_arg)
    
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

# ================== 👑 𝐒𝐔𝐃𝐎/𝐎𝐖𝐍𝐄𝐑 ==================

async def sudo_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    msg = (
        "🔐 <b>𝐒𝐮𝐝𝐨 𝐏𝐚𝐧𝐞𝐥</b>\n\n"
        "‣ <code>/addcoins [amt] [user]</code>\n"
        "‣ <code>/rmcoins [amt] [user]</code>\n"
        "‣ <code>/freerevive [user]</code>\n"
        "‣ <code>/broadcast -user/-group [msg]</code>\n"
        "‣ <code>/sudolist</code>\n\n"
        "👑 <b>𝐎𝐰𝐧𝐞𝐫:</b>\n"
        "‣ <code>/addsudo [user]</code>\n"
        "‣ <code>/rmsudo [user]</code>\n"
        "‣ <code>/cleandb</code>\n"
    )
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def sudolist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "👑 <b>𝐎𝐰𝐧𝐞𝐫 & 𝐒𝐮𝐝𝐨𝐞𝐫𝐬:</b>\n\n"
    
    # 1. Fetch Owner Info
    owner_doc = get_user_from_db(OWNER_ID)
    if not owner_doc:
        # If owner not in DB, try to fetch from Telegram
        try:
            chat_owner = await context.bot.get_chat(OWNER_ID)
            owner_name = chat_owner.first_name
        except:
            owner_name = "Owner"
        msg += f"👑 <a href='tg://user?id={OWNER_ID}'><b>{html.escape(owner_name)}</b></a> (Owner)\n"
    else:
        msg += f"👑 {get_mention(owner_doc)} (Owner)\n"
    
    # 2. Fetch Sudoers Info
    for uid in SUDO_USERS:
        if uid == OWNER_ID: continue
        u_doc = get_user_from_db(uid)
        
        if u_doc:
            msg += f"👮 {get_mention(u_doc)}\n"
        else:
            # Try fetch if not in DB
            try:
                chat_sudo = await context.bot.get_chat(uid)
                msg += f"👮 <a href='tg://user?id={uid}'><b>{html.escape(chat_sudo.first_name)}</b></a>\n"
            except:
                msg += f"👮 <code>{uid}</code>\n"
                
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    
    # Usage: /broadcast -user <msg> or /broadcast -group <msg> or reply
    args = context.args
    msg_to_send = None
    target_type = None # 'user' or 'group'
    
    if not args: return await update.message.reply_text("⚠️ <b>Usage:</b> <code>/broadcast -user <msg></code>", parse_mode=ParseMode.HTML)
    
    flag = args[0]
    if flag == "-user": target_type = "user"
    elif flag == "-group": target_type = "group"
    else: return await update.message.reply_text("⚠️ Use <code>-user</code> or <code>-group</code> flag.", parse_mode=ParseMode.HTML)
    
    # Determine Content
    if update.message.reply_to_message:
        msg_to_send = update.message.reply_to_message.text or update.message.reply_to_message.caption
    else:
        if len(args) < 2: return await update.message.reply_text("⚠️ Where is the message?", parse_mode=ParseMode.HTML)
        msg_to_send = " ".join(args[1:])
        
    await update.message.reply_text(f"⏳ <b>Broadcasting to {target_type}s...</b>", parse_mode=ParseMode.HTML)
    
    count = 0
    targets = users_collection.find({}) if target_type == "user" else groups_collection.find({})
    
    for doc in targets:
        cid = doc.get("user_id") if target_type == "user" else doc.get("chat_id")
        try:
            await context.bot.send_message(chat_id=cid, text=msg_to_send, parse_mode=ParseMode.HTML)
            count += 1
            await asyncio.sleep(0.05) # Rate Limit Safety
        except Forbidden:
            # Blocked bot or kicked from group
            if target_type == "user": users_collection.delete_one({"user_id": cid})
            else: groups_collection.delete_one({"chat_id": cid})
        except Exception: pass
        
    await update.message.reply_text(f"✅ <b>Broadcast Complete!</b>\nSent to {count} {target_type}s.", parse_mode=ParseMode.HTML)

# --- Confirmation & Admin Logic ---

def get_confirm_keyboard(action, args_str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ 𝐘𝐞𝐬", callback_data=f"cnf|{action}|{args_str}"), InlineKeyboardButton("❌ 𝐍𝐨", callback_data="cnf|cancel|0")]])

async def ask_confirm(update: Update, text: str, action: str, args_str: str):
    await update.message.reply_text(f"⚠️ <b>Wait!</b> {text}\nAre you sure?", parse_mode=ParseMode.HTML, reply_markup=get_confirm_keyboard(action, args_str))

async def addsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target, error = await resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /addsudo <target>", parse_mode=ParseMode.HTML)
    if target['user_id'] in SUDO_USERS: return await update.message.reply_text("⚠️ Already Sudoer.", parse_mode=ParseMode.HTML)
    await ask_confirm(update, f"Promote {get_mention(target)}?", "addsudo", str(target['user_id']))

async def rmsudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID: return
    target, error = await resolve_target(update, context)
    if not target: return await update.message.reply_text(error or "Usage: /rmsudo <target>", parse_mode=ParseMode.HTML)
    if target['user_id'] not in SUDO_USERS: return await update.message.reply_text("⚠️ Not a Sudoer.", parse_mode=ParseMode.HTML)
    await ask_confirm(update, f"Demote {get_mention(target)}?", "rmsudo", str(target['user_id']))

async def addcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    args = context.args
    if not args: return await update.message.reply_text("Usage: /addcoins <amt> <user>", parse_mode=ParseMode.HTML)
    try: amt = int(args[0])
    except: return await update.message.reply_text("Invalid amount.", parse_mode=ParseMode.HTML)
    
    target_arg = args[1] if len(args) > 1 else None
    target, error = await resolve_target(update, context, specific_arg=target_arg)
    
    if not target: return await update.message.reply_text(error or "No target.", parse_mode=ParseMode.HTML)
    await ask_confirm(update, f"Give <b>{format_money(amt)}</b> to {get_mention(target)}?", "addcoins", f"{target['user_id']}|{amt}")

async def rmcoins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    args = context.args
    if not args: return await update.message.reply_text("Usage: /rmcoins <amt> <user>", parse_mode=ParseMode.HTML)
    try: amt = int(args[0])
    except: return await update.message.reply_text("Invalid amount.", parse_mode=ParseMode.HTML)
    
    target_arg = args[1] if len(args) > 1 else None
    target, error = await resolve_target(update, context, specific_arg=target_arg)
    
    if not target: return await update.message.reply_text(error or "No target.", parse_mode=ParseMode.HTML)
    await ask_confirm(update, f"Remove <b>{format_money(amt)}</b> from {get_mention(target)}?", "rmcoins", f"{target['user_id']}|{amt}")

async def freerevive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in SUDO_USERS: return
    target, error = await resolve_target(update, context)
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
        groups_collection.delete_many({}) # Clear groups too
        await query.message.edit_text("🗑️ <b>DATABASE WIPED!</b>", parse_mode=ParseMode.HTML)

# ================== 🕵️ 𝐋𝐎𝐆𝐆𝐈𝐍𝐆 ==================

async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.my_chat_member: return
    new = update.my_chat_member.new_chat_member
    chat = update.my_chat_member.chat
    user = update.my_chat_member.from_user
    
    # Track group in DB
    track_group(chat)

    if new.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        link = "No Link"
        if new.status == ChatMember.ADMINISTRATOR:
            try: link = await context.bot.export_chat_invite_link(chat.id)
            except: pass
        await send_log(context, f"🆕 <b>Bot Added!</b>\n📍 {chat.title}\n👤 By: {get_mention(user)}\n🔗 {link}")
    
    elif new.status in [ChatMember.LEFT, ChatMember.BANNED]:
        # Remove from groups DB if kicked
        groups_collection.delete_one({"chat_id": chat.id})
        await send_log(context, f"❌ <b>Bot Removed/Left</b>\n📍 {chat.title}\n👤 By: {get_mention(user)}")

# ================== 𝐌𝐀𝐈𝐍 ==================

app = Flask(__name__)
@app.route('/')
def health(): return "Baka Bot Ultimate Alive"
def run_flask(): app.run(host='0.0.0.0', port=PORT)

async def set_bot_commands(application):
    commands = [
        BotCommand("start", "𝐒𝐭𝐚𝐫𝐭"), BotCommand("help", "𝐇𝐞𝐥𝐩"),
        BotCommand("register", "𝐉𝐨𝐢𝐧"), BotCommand("bal", "𝐁𝐚𝐥𝐚𝐧𝐜𝐞"),
        BotCommand("ranking", "𝐓𝐨𝐩𝐬"), BotCommand("give", "𝐓𝐫𝐚𝐧𝐬𝐟𝐞𝐫"),
        BotCommand("kill", "𝐀𝐭𝐭𝐚𝐜𝐤"), BotCommand("rob", "𝐒𝐭𝐞𝐚𝐥"),
        BotCommand("protect", "𝐒𝐡𝐢𝐞𝐥𝐝"), BotCommand("revive", "𝐑𝐞𝐯𝐢𝐯𝐞"),
    ]
    await application.bot.set_my_commands(commands)
    await send_log(application, f"🌟 <b>Baka Bot Restarted!</b>\nOnline and Ready! (⁠≧⁠▽⁠≦⁠)")

if __name__ == '__main__':
    Thread(target=run_flask).start()
    if not TOKEN: print("CRITICAL: BOT_TOKEN missing.")
    else:
        app_bot = ApplicationBuilder().token(TOKEN).build()
        
        # User
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

        # Admin
        app_bot.add_handler(CommandHandler("sudo", sudo_help))
        app_bot.add_handler(CommandHandler("sudolist", sudolist))
        app_bot.add_handler(CommandHandler("broadcast", broadcast)) # NEW
        app_bot.add_handler(CommandHandler("addsudo", addsudo))
        app_bot.add_handler(CommandHandler("rmsudo", rmsudo))
        app_bot.add_handler(CommandHandler("addcoins", addcoins))
        app_bot.add_handler(CommandHandler("rmcoins", rmcoins))
        app_bot.add_handler(CommandHandler("freerevive", freerevive))
        app_bot.add_handler(CommandHandler("cleandb", cleandb))
        app_bot.add_handler(CallbackQueryHandler(confirm_handler, pattern="^cnf\|"))
        app_bot.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
        
        # Track messages in groups for broadcasting database
        app_bot.add_handler(MessageHandler(filters.ChatType.GROUPS, lambda u, c: track_group(u.effective_chat)))

        app_bot.post_init = set_bot_commands
        print(f"Baka Bot Started on Port {PORT}...")
        app_bot.run_polling()