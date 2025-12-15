import os
from pyrogram import Client, filters
# FIXED: Removed ChatPermissions from enums
from pyrogram.enums import ChatType, ChatMemberStatus
# FIXED: Added ChatPermissions to types
from pyrogram.types import Message, ChatPermissions
from motor.motor_asyncio import AsyncIOMotorClient
# IMPORT CONFIG
from config import MONGO_URL

# --- DATABASE CONNECTION (For Warns) ---
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot
users_col = db.users

# --- HELPER: CHECK ADMIN ---
async def check_admin(message: Message):
    """Checks if the user is an Admin or Owner."""
    if message.chat.type == ChatType.PRIVATE:
        return False
    try:
        mem = await message.chat.get_member(message.from_user.id)
        return mem.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

# --- ADMIN ACTIONS (Ban, Kick, Mute, Promote, etc) ---
@Client.on_message(filters.command(["ban", "unban", "kick", "mute", "unmute", "pin", "unpin", "demote", "promote", "del"], prefixes=".") & filters.group)
async def admin_actions(client: Client, message: Message):
    if not await check_admin(message):
        return
    
    if not message.reply_to_message:
        return await message.reply_text("⚠️ Reply to a user to perform this action.")

    cmd = message.command[0]
    user = message.reply_to_message.from_user
    chat_id = message.chat.id
    user_id = user.id

    try:
        # BAN
        if cmd == "ban":
            await client.ban_chat_member(chat_id, user_id)
            await message.reply_text(f"🚫 **Banned** {user.mention}!")
        
        # UNBAN
        elif cmd == "unban":
            await client.unban_chat_member(chat_id, user_id)
            await message.reply_text(f"✅ **Unbanned** {user.mention}!")

        # KICK (Ban + Unban)
        elif cmd == "kick":
            await client.ban_chat_member(chat_id, user_id)
            await client.unban_chat_member(chat_id, user_id)
            await message.reply_text(f"👢 **Kicked** {user.mention}!")

        # MUTE
        elif cmd == "mute":
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
            await message.reply_text(f"🤐 **Muted** {user.mention}!")

        # UNMUTE
        elif cmd == "unmute":
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=True))
            await message.reply_text(f"🗣️ **Unmuted** {user.mention}!")

        # PIN
        elif cmd == "pin":
            await message.reply_to_message.pin()
            await message.reply_text("📌 Message Pinned!")

        # UNPIN
        elif cmd == "unpin":
            await message.reply_to_message.unpin()
            await message.reply_text("📌 Message Unpinned!")

        # DELETE MESSAGE
        elif cmd == "del":
            await message.reply_to_message.delete()
            await message.delete()

        # DEMOTE
        elif cmd == "demote":
            await client.promote_chat_member(
                chat_id, user_id,
                privileges=ChatPermissions(
                    can_change_info=False,
                    can_invite_users=False,
                    can_delete_messages=False,
                    can_restrict_members=False,
                    can_pin_messages=False,
                    can_promote_members=False,
                    can_manage_chat=False,
                    can_manage_video_chats=False
                )
            )
            await message.reply_text(f"📉 **Demoted** {user.mention}!")

        # PROMOTE
        elif cmd == "promote":
            await client.promote_chat_member(
                chat_id, user_id,
                privileges=ChatPermissions(
                    can_change_info=True,
                    can_invite_users=True,
                    can_delete_messages=True,
                    can_restrict_members=True,
                    can_pin_messages=True,
                    can_promote_members=False,
                    can_manage_chat=True,
                    can_manage_video_chats=True
                )
            )
            await message.reply_text(f"👮‍♂️ **Promoted** {user.mention} to Admin!")
            
    except Exception as e:
        # Print actual error to logs for debugging if needed
        print(f"Admin Action Error: {e}")
        await message.reply_text(f"❌ **Error:** I need Admin Rights (or higher rank) to do this!")

# --- WARN SYSTEM (With Database) ---
@Client.on_message(filters.command(["warn", "unwarn"], prefixes=".") & filters.group)
async def warn_system(client: Client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return

    cmd = message.command[0]
    user = message.reply_to_message.from_user
    chat_id = message.chat.id

    # Get User Data
    user_data = await users_col.find_one({"_id": user.id})
    if not user_data:
        await users_col.insert_one({"_id": user.id, "warns": 0})
        warns = 0
    else:
        warns = user_data.get("warns", 0)

    if cmd == "warn":
        warns += 1
        await users_col.update_one({"_id": user.id}, {"$set": {"warns": warns}})
        
        if warns >= 3:
            try:
                await client.ban_chat_member(chat_id, user.id)
                await users_col.update_one({"_id": user.id}, {"$set": {"warns": 0}})
                await message.reply_text(f"🚫 {user.mention} has been banned! (3/3 Warns)")
            except:
                await message.reply_text(f"⚠️ {user.mention} reached 3 warns but I can't ban them!")
        else:
            await message.reply_text(f"⚠️ **Warned** {user.mention}! ({warns}/3)")

    elif cmd == "unwarn":
        if warns > 0:
            warns -= 1
            await users_col.update_one({"_id": user.id}, {"$set": {"warns": warns}})
            await message.reply_text(f"📉 **Unwarned** {user.mention}. ({warns}/3)")
        else:
            await message.reply_text(f"{user.mention} has no warns!")

# --- INFO COMMANDS ---
@Client.on_message(filters.command("adminlist"))
async def adminlist(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE: return
    admins = []
    async for m in client.get_chat_members(message.chat.id, filter=ChatMemberStatus.ADMINISTRATOR):
        if m.user: admins.append(m.user.mention)
    
    await message.reply_text("👮‍♂️ **Group Staff:**\n" + "\n".join(admins))

@Client.on_message(filters.command("owner"))
async def owner_tag(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE: return
    async for m in client.get_chat_members(message.chat.id, filter=ChatMemberStatus.OWNER):
        if m.user: await message.reply_text(f"👑 **Owner:** {m.user.mention}")

# --- GROUP SETTINGS (OPEN/CLOSE) ---
@Client.on_message(filters.command("open"))
async def open_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ You can use these commands in groups only.")
    if not await check_admin(message): return
    await message.reply_text("✅ All economy commands have been enabled.")

@Client.on_message(filters.command("close"))
async def close_cmd(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("❌ You can use these commands in groups only.")
    if not await check_admin(message): return
    await message.reply_text("🚫 All economy commands have been disabled.")
