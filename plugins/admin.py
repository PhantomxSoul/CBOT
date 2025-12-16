import time
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.types import Message, ChatPermissions
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot
users_col = db.users

# --- HELPERS ---

async def check_admin(message: Message):
    if message.chat.type == ChatType.PRIVATE: return False
    try:
        mem = await message.chat.get_member(message.from_user.id)
        return mem.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

async def get_target_user(client, message):
    if message.reply_to_message:
        return message.reply_to_message.from_user
    if len(message.command) > 1:
        try:
            user_input = message.command[1]
            if user_input.isdigit(): return await client.get_users(int(user_input))
            else: return await client.get_users(user_input)
        except: pass
    return None

def get_time_seconds(time_str):
    unit = time_str[-1].lower()
    if unit not in ['m', 'h', 'd']: return 0
    try: val = int(time_str[:-1])
    except: return 0
    if unit == 'm': return val * 60
    elif unit == 'h': return val * 3600
    elif unit == 'd': return val * 86400
    return 0

# --- COMMANDS ---

@Client.on_message(filters.command(["ban", "unban", "kick"], prefixes=["/", "."]) & filters.group)
async def ban_kick_logic(client, message):
    if not await check_admin(message): return
    user = await get_target_user(client, message)
    if not user: return await message.reply_text("❌ User not found. Reply or use ID.")
    
    cmd = message.command[0]
    try:
        if cmd == "ban":
            await client.ban_chat_member(message.chat.id, user.id)
            await message.reply_text(f"🚫 Banned {user.mention}!")
        elif cmd == "unban":
            await client.unban_chat_member(message.chat.id, user.id)
            await message.reply_text(f"✅ Unbanned {user.mention}!")
        elif cmd == "kick":
            await client.ban_chat_member(message.chat.id, user.id)
            await client.unban_chat_member(message.chat.id, user.id)
            await message.reply_text(f"👢 Kicked {user.mention}!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@Client.on_message(filters.command(["mute", "unmute"], prefixes=["/", "."]) & filters.group)
async def mute_logic(client, message):
    if not await check_admin(message): return
    user = await get_target_user(client, message)
    if not user: return await message.reply_text("❌ User not found.")
    
    cmd = message.command[0]
    if cmd == "unmute":
        try:
            await client.restrict_chat_member(message.chat.id, user.id, ChatPermissions(can_send_messages=True))
            await message.reply_text(f"🗣️ Unmuted {user.mention}!")
        except: await message.reply_text("❌ Error.")
        return

    # Time Logic
    seconds = 0
    reason = "Forever"
    args = message.command
    if message.reply_to_message and len(args) > 1:
        seconds = get_time_seconds(args[1])
        if seconds > 0: reason = args[1]
    elif len(args) > 2:
        seconds = get_time_seconds(args[2])
        if seconds > 0: reason = args[2]

    try:
        until_val = datetime.now() + timedelta(seconds=seconds) if seconds > 0 else datetime.now() + timedelta(days=3650)
        await client.restrict_chat_member(message.chat.id, user.id, ChatPermissions(can_send_messages=False), until_date=until_val)
        await message.reply_text(f"🤐 Muted {user.mention} for **{reason}**!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@Client.on_message(filters.command(["warn", "unwarn"], prefixes=["/", "."]) & filters.group)
async def warn_logic(client, message):
    if not await check_admin(message): return
    user = await get_target_user(client, message)
    if not user: return await message.reply_text("❌ User not found.")
    
    user_data = await users_col.find_one({"_id": user.id})
    warns = user_data.get("warns", 0) if user_data else 0
    
    cmd = message.command[0]
    if cmd == "warn":
        warns += 1
        await users_col.update_one({"_id": user.id}, {"$set": {"warns": warns}}, upsert=True)
        if warns >= 3:
            try:
                await client.ban_chat_member(message.chat.id, user.id)
                await users_col.update_one({"_id": user.id}, {"$set": {"warns": 0}})
                await message.reply_text(f"🚫 {user.mention} banned (3/3 warns)!")
            except: await message.reply_text("⚠️ 3 warns reached, but I can't ban.")
        else:
            await message.reply_text(f"⚠️ Warned {user.mention}! ({warns}/3)")
    elif cmd == "unwarn":
        if warns > 0:
            warns -= 1
            await users_col.update_one({"_id": user.id}, {"$set": {"warns": warns}})
            await message.reply_text(f"📉 Unwarned {user.mention}. ({warns}/3)")
        else:
            await message.reply_text("User has 0 warns.")

@Client.on_message(filters.command(["pin", "unpin", "d"], prefixes=["/", "."]) & filters.group)
async def msg_logic(client, message):
    if not await check_admin(message): return
    if not message.reply_to_message: return await message.reply_text("Reply to a message!")
    try:
        if message.command[0] == "pin": await message.reply_to_message.pin(); await message.reply_text("📌 Pinned!")
        elif message.command[0] == "unpin": await message.reply_to_message.unpin(); await message.reply_text("📌 Unpinned!")
        elif message.command[0] == "d": await message.reply_to_message.delete(); await message.delete()
    except: pass
