import time
import asyncio
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.types import Message, ChatPermissions
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

# --- DATABASE ---
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot
users_col = db.users

# --- HELPER FUNCTIONS ---

async def check_admin(message: Message):
    """Check if user is Admin/Owner"""
    if message.chat.type == ChatType.PRIVATE: return False
    try:
        mem = await message.chat.get_member(message.from_user.id)
        return mem.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

async def get_target_user(client, message):
    """Extracts user from Reply OR Command Argument"""
    if message.reply_to_message:
        return message.reply_to_message.from_user
    
    if len(message.command) > 1:
        try:
            # Try to resolve by ID or Username
            user_id = message.command[1]
            if user_id.isdigit():
                return await client.get_users(int(user_id))
            else:
                return await client.get_users(user_id)
        except:
            return None
    return None

def get_time_seconds(time_str):
    """Parses 1m, 1h, 1d into seconds"""
    unit = time_str[-1].lower()
    if unit not in ['m', 'h', 'd']: return 0
    try:
        val = int(time_str[:-1])
    except: return 0
    
    if unit == 'm': return val * 60
    if unit == 'h': return val * 3600
    if unit == 'd': return val * 86400
    return 0

# --- COMMANDS ---

# 1. BAN & UNBAN
@Client.on_message(filters.command(["ban", "unban", "kick"], prefixes=["/", "."]) & filters.group)
async def ban_kick_logic(client, message):
    if not await check_admin(message): return
    user = await get_target_user(client, message)
    if not user: return await message.reply_text("❌ Please reply to a user or give their ID/Username.")
    
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
        await message.reply_text("❌ Error: I need Admin Rights!")

# 2. MUTE & UNMUTE
@Client.on_message(filters.command(["mute", "unmute"], prefixes=["/", "."]) & filters.group)
async def mute_logic(client, message):
    if not await check_admin(message): return
    user = await get_target_user(client, message)
    if not user: return await message.reply_text("❌ Please reply to a user or give ID.")
    
    cmd = message.command[0]
    if cmd == "unmute":
        try:
            await client.restrict_chat_member(message.chat.id, user.id, ChatPermissions(can_send_messages=True))
            await message.reply_text(f"🗣️ Unmuted {user.mention}!")
        except: await message.reply_text("❌ Error.")
        return

    # Logic for Mute Time
    # If replying: command is [.mute, time] -> len 2
    # If ID: command is [.mute, ID, time] -> len 3
    
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
        until = datetime.now() + timedelta(seconds=seconds) if seconds > 0 else datetime.now() + timedelta(days=3650)
        # Fix: Pyrogram expects until_date as a datetime object or timestamp
        until_val = int(time.time() + seconds) if seconds > 0 else 0
        
        await client.restrict_chat_member(
            message.chat.id, 
            user.id, 
            ChatPermissions(can_send_messages=False),
            until_date=until_val
        )
        await message.reply_text(f"🤐 Muted {user.mention} for **{reason}**!")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

# 3. PROMOTE, DEMOTE, TITLE
@Client.on_message(filters.command(["promote", "demote", "title"], prefixes=["/", "."]) & filters.group)
async def promote_logic(client, message):
    if not await check_admin(message): return
    user = await get_target_user(client, message)
    if not user: return await message.reply_text("❌ Target not found.")
    
    cmd = message.command[0]
    
    try:
        if cmd == "demote":
            await client.promote_chat_member(
                message.chat.id, user.id,
                privileges=ChatPermissions(can_change_info=False) # Revoke all
            )
            await message.reply_text(f"📉 Demoted {user.mention}!")
            return

        if cmd == "title":
            if len(message.command) < 2 + (0 if message.reply_to_message else 1):
                return await message.reply_text("❌ Usage: .title [reply/id] [Custom Title]")
            
            # Extract title string
            title_parts = message.command[1:] if message.reply_to_message else message.command[2:]
            title = " ".join(title_parts)
            
            await client.set_administrator_custom_title(message.chat.id, user.id, title)
            await message.reply_text(f"🏷️ Title set for {user.mention}: **{title}**")
            return

        # PROMOTE LEVELS
        level = "1"
        if len(message.command) > (1 if message.reply_to_message else 2):
            level = message.command[-1]
            
        perms = ChatPermissions(can_manage_chat=True) # Default
        if level == "1": # Basic
            perms = ChatPermissions(can_manage_chat=True, can_invite_users=True, can_delete_messages=True)
        elif level == "2": # Mod
            perms = ChatPermissions(can_manage_chat=True, can_invite_users=True, can_delete_messages=True, can_restrict_members=True, can_pin_messages=True)
        elif level == "3": # Full
            perms = ChatPermissions(can_manage_chat=True, can_invite_users=True, can_delete_messages=True, can_restrict_members=True, can_pin_messages=True, can_promote_members=True, can_change_info=True)
            
        await client.promote_chat_member(message.chat.id, user.id, privileges=perms)
        await message.reply_text(f"👮‍♂️ Promoted {user.mention} to Admin (Level {level})!")
            
    except Exception as e:
        await message.reply_text("❌ Failed. I might need Add Admin rights.")

# 4. PIN, UNPIN, DELETE
@Client.on_message(filters.command(["pin", "unpin", "d"], prefixes=["/", "."]) & filters.group)
async def msg_logic(client, message):
    if not await check_admin(message): return
    if not message.reply_to_message: return await message.reply_text("❌ Reply to a message!")
    
    cmd = message.command[0]
    try:
        if cmd == "pin":
            await message.reply_to_message.pin()
            await message.reply_text("📌 Pinned!")
        elif cmd == "unpin":
            await message.reply_to_message.unpin()
            await message.reply_text("📌 Unpinned!")
        elif cmd == "d":
            await message.reply_to_message.delete()
            await message.delete()
    except:
        await message.reply_text("❌ Error.")

# 5. WARN SYSTEM
@Client.on_message(filters.command(["warn", "unwarn"], prefixes=["/", "."]) & filters.group)
async def warn_logic(client, message):
    if not await check_admin(message): return
    user = await get_target_user(client, message)
    if not user: return await message.reply_text("❌ Target not found.")
    
    user_data = await users_col.find_one({"_id": user.id})
    if not user_data: 
        await users_col.insert_one({"_id": user.id, "warns": 0})
        warns = 0
    else:
        warns = user_data.get("warns", 0)
        
    cmd = message.command[0]
    if cmd == "warn":
        warns += 1
        await users_col.update_one({"_id": user.id}, {"$set": {"warns": warns}})
        if warns >= 3:
            try:
                await client.ban_chat_member(message.chat.id, user.id)
                await users_col.update_one({"_id": user.id}, {"$set": {"warns": 0}})
                await message.reply_text(f"🚫 {user.mention} banned (3/3 warns)!")
            except: await message.reply_text("⚠️ 3 warns reached but cannot ban.")
        else:
            await message.reply_text(f"⚠️ Warned {user.mention}! ({warns}/3)")
            
    elif cmd == "unwarn":
        if warns > 0:
            warns -= 1
            await users_col.update_one({"_id": user.id}, {"$set": {"warns": warns}})
            await message.reply_text(f"📉 Unwarned {user.mention}. ({warns}/3)")
        else:
            await message.reply_text("User has 0 warns.")
