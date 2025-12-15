import time
import os
import sys
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, OWNER_ID

# --- DATABASE CONNECTION ---
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot
users_col = db.users

# --- HELPER: CHECK OWNER ---
async def check_owner(message: Message):
    return message.from_user.id == OWNER_ID

# ---------------- OWNER COMMANDS ---------------- #

@Client.on_message(filters.command("sudo") & filters.private)
async def sudo_menu(client: Client, message: Message):
    if not await check_owner(message): return
    
    txt = (
        "👑 **Owner / Sudo Dashboard**\n\n"
        "📊 **Stats:**\n"
        "• /status - Check System Health & Ping\n"
        "• /stats - Check Total Users & DB Size\n\n"
        "📢 **Broadcast:**\n"
        "• /broadcast [reply/text] - Send msg to ALL users\n\n"
        "💎 **Premium Management:**\n"
        "• /makepremium [id] - Give Premium\n"
        "• /removepremium [id] - Remove Premium\n"
        "• /premiumlist - List all Premium Users\n\n"
        "⚙️ **System:**\n"
        "• /restart - Restart the Bot\n"
        "• /logs - Get Heroku Logs (Requires Heroku API Key)"
    )
    await message.reply_text(txt)

@Client.on_message(filters.command("status"))
async def status_cmd(client: Client, message: Message):
    # Public command (Safe to show ping to everyone)
    start = time.time()
    msg = await message.reply_text("🔄 Checking System...")
    end = time.time()
    ping = int((end - start) * 1000)
    
    await msg.edit_text(
        f"🤖 **System Status**\n\n"
        f"📶 **Ping:** `{ping}ms`\n"
        f"✅ **Service:** Online\n"
        f"🧠 **AI Engine:** GitHub (GPT-4o) + Pollinations\n"
        f"👑 **Owner:** [{OWNER_ID}](tg://user?id={OWNER_ID})"
    )

@Client.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats_cmd(client: Client, message: Message):
    msg = await message.reply_text("🔄 Counting Users...")
    count = await users_col.count_documents({})
    prem_count = await users_col.count_documents({"premium": True})
    
    await msg.edit_text(
        f"📊 **Bot Statistics**\n\n"
        f"👤 **Total Users:** `{count}`\n"
        f"💎 **Premium Users:** `{prem_count}`\n"
    )

@Client.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_cmd(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text("⚠️ Usage: Reply to a message or `/broadcast Hello`")
    
    msg = await message.reply_text("📣 **Broadcasting started...**")
    
    users = users_col.find({})
    total = await users_col.count_documents({})
    sent = 0
    failed = 0
    
    async for user in users:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy(user['_id'])
            else:
                await client.send_message(user['_id'], message.text.split(None, 1)[1])
            sent += 1
        except:
            failed += 1
            
    await msg.edit_text(
        f"✅ **Broadcast Complete**\n\n"
        f"👥 Total: `{total}`\n"
        f"✅ Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`"
    )

# ---------------- PREMIUM MANAGEMENT ---------------- #

@Client.on_message(filters.command("makepremium") & filters.user(OWNER_ID))
async def make_premium(client: Client, message: Message):
    try:
        user_id = int(message.command[1])
        await users_col.update_one({"_id": user_id}, {"$set": {"premium": True}})
        await message.reply_text(f"✅ User `{user_id}` is now **Premium**! 💎")
        # Notify user
        try: await client.send_message(user_id, "💎 **Congratulations!** You have been upgraded to Premium!")
        except: pass
    except:
        await message.reply_text("⚠️ Usage: `/makepremium 12345678`")

@Client.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def remove_premium(client: Client, message: Message):
    try:
        user_id = int(message.command[1])
        await users_col.update_one({"_id": user_id}, {"$set": {"premium": False}})
        await message.reply_text(f"🚫 User `{user_id}` is no longer Premium.")
    except:
        await message.reply_text("⚠️ Usage: `/removepremium 12345678`")

@Client.on_message(filters.command("premiumlist") & filters.user(OWNER_ID))
async def premium_list(client: Client, message: Message):
    users = users_col.find({"premium": True})
    txt = "💎 **Premium Users:**\n\n"
    count = 0
    async for u in users:
        count += 1
        txt += f"{count}. `{u['_id']}` - {u.get('name', 'Unknown')}\n"
    
    if count == 0:
        await message.reply_text("No premium users found.")
    else:
        await message.reply_text(txt)

# ---------------- SYSTEM ---------------- #

@Client.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def restart_bot(client: Client, message: Message):
    await message.reply_text("🔄 Restarting Bot...")
    os.execl(sys.executable, sys.executable, *sys.argv)
