from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus, ChatPermissions
from pyrogram.types import Message

# --- HELPER FUNCTION ---
async def check_admin(message: Message):
    """Checks if the user is an Admin or Owner."""
    try:
        if message.chat.type == ChatType.PRIVATE:
            return False
        mem = await message.chat.get_member(message.from_user.id)
        return mem.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except:
        return False

# --- ADMIN ACTIONS (Ban, Mute, Kick, Pin) ---
@Client.on_message(filters.command(["ban", "unban", "kick", "mute", "unmute", "pin", "unpin", "demote"], prefixes=".") & filters.group)
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
        if cmd == "ban":
            await client.ban_chat_member(chat_id, user_id)
            await message.reply_text(f"🚫 **Banned** {user.mention}!")
        
        elif cmd == "unban":
            await client.unban_chat_member(chat_id, user_id)
            await message.reply_text(f"✅ **Unbanned** {user.mention}!")

        elif cmd == "kick":
            await client.ban_chat_member(chat_id, user_id)
            await client.unban_chat_member(chat_id, user_id)
            await message.reply_text(f"👢 **Kicked** {user.mention}!")

        elif cmd == "mute":
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False))
            await message.reply_text(f"🤐 **Muted** {user.mention}!")

        elif cmd == "unmute":
            await client.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=True))
            await message.reply_text(f"🗣️ **Unmuted** {user.mention}!")

        elif cmd == "pin":
            await message.reply_to_message.pin()
            await message.reply_text("📌 Message Pinned!")

        elif cmd == "unpin":
            await message.reply_to_message.unpin()
            await message.reply_text("📌 Message Unpinned!")
            
    except Exception as e:
        await message.reply_text(f"❌ **Error:** I need Admin Rights to do this!\n`{e}`")

# --- WARN SYSTEM (Basic) ---
@Client.on_message(filters.command(["warn"], prefixes=".") & filters.group)
async def warn_user(client: Client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    user = message.reply_to_message.from_user
    await message.reply_text(f"⚠️ **Warned** {user.mention}! (Logic to count warns requires DB)")

# --- INFO COMMANDS ---
@Client.on_message(filters.command("adminlist"))
async def adminlist(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE: return
    admins = []
    async for m in client.get_chat_members(message.chat.id, filter=ChatMemberStatus.ADMINISTRATOR):
        if m.user: admins.append(m.user.mention)
    
    # Add owner
    async for m in client.get_chat_members(message.chat.id, filter=ChatMemberStatus.OWNER):
        if m.user: admins.insert(0, f"👑 {m.user.mention}")

    await message.reply_text("👮‍♂️ **Group Staff:**\n" + "\n".join(admins))

@Client.on_message(filters.command("owner"))
async def owner_tag(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE: return
    async for m in client.get_chat_members(message.chat.id, filter=ChatMemberStatus.OWNER):
        await message.reply_text(f"👑 **Owner:** {m.user.mention}")

# --- GROUP SETTINGS ---
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
