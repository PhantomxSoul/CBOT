import os
import time
import random
import asyncio
import requests
import urllib.parse
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatType, ChatAction, ParseMode, ChatMemberStatus
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Message, 
    CallbackQuery, 
    ChatPermissions,
    BotCommand
)

# ---------------- CONFIGURATION ---------------- #
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
MONGO_URL = os.environ.get("MONGO_URL")
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))

app = Client("baka_master", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- DATABASE (MONGODB) ---------------- #
if not MONGO_URL:
    print("⚠️ MONGO_URL is missing! Bot will crash.")
    exit()

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot
users_col = db.users
groups_col = db.groups

async def get_user(user_id, name="User"):
    user = await users_col.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id,
            "name": name,
            "balance": 0,
            "status": "alive",
            "kills": 0,
            "premium": False,
            "last_daily": 0,
            "protected_until": 0,
            "warns": 0,
            "claimed_group": False
        }
        await users_col.insert_one(user)
    return user

async def update_user(user_id, data):
    await users_col.update_one({"_id": user_id}, {"$set": data})

async def log_event(text):
    if LOG_CHANNEL_ID != 0:
        try:
            await app.send_message(LOG_CHANNEL_ID, text, disable_web_page_preview=True)
        except: pass

# ---------------- 1. AI ENGINE (DUAL CORE) ---------------- #

def ai_github_models(user_text):
    if not GITHUB_TOKEN: return None
    try:
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GITHUB_TOKEN}"}
        payload = {
            "messages": [
                {"role": "system", "content": "You are Baka, a sassy female Telegram bot. Reply in Hinglish (Hindi+English). Be savage, cute, use emojis."},
                {"role": "user", "content": user_text}
            ],
            "model": "gpt-4o",
            "temperature": 0.8,
            "max_tokens": 200
        }
        response = requests.post(url, headers=headers, json=payload, timeout=8)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except: pass
    return None

def ai_pollinations(user_text):
    try:
        seed = random.randint(1, 99999)
        system = "You are Baka, a sassy female bot. Reply in Hinglish. Be savage but cute. User says: "
        encoded = urllib.parse.quote(f"{system} {user_text}")
        url = f"https://text.pollinations.ai/{encoded}?seed={seed}&model=openai"
        res = requests.get(url, timeout=8)
        if res.status_code == 200: return res.text
    except: pass
    return None

@app.on_message(filters.text & ~filters.regex(r"^[/\.]"))
async def chat_handler(client, message: Message):
    is_private = message.chat.type == ChatType.PRIVATE
    is_mentioned = message.mentioned
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == client.me.id

    if is_private or is_mentioned or is_reply:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # 1. Try GitHub (Smartest)
        reply = await asyncio.to_thread(ai_github_models, message.text)
        
        # 2. Fallback to Pollinations (Unstoppable)
        if not reply:
            reply = await asyncio.to_thread(ai_pollinations, message.text)
            
        # 3. Final Fallback
        if not reply:
            reply = "Network issue hai yaar... baad mein aana! 😵‍💫"
            
        await message.reply_text(reply)

# ---------------- 2. START, HELP & STATUS ---------------- #

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    user = await get_user(message.from_user.id, message.from_user.first_name)
    
    # Logger
    if message.chat.type == ChatType.PRIVATE:
        log_text = (
            f"🚀 **New User Started Bot**\n\n"
            f"👤 **User:** [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n"
            f"🆔 **ID:** `{message.from_user.id}`"
        )
        await log_event(log_text)

    txt = (
        f"✨ 𝐇𝐞𝐲 {message.from_user.mention} ~\n"
        f"𖦹 𝒀𝒐𝒖'𝒓𝒆 𝒕𝒂𝒍𝒌𝒊𝒏𝒈 𝒕𝒐 𝑩𝒂𝒌𝒂, 𝒂 𝒔𝒂𝒔𝒔𝒚 𝒄𝒖𝒕𝒊𝒆 𝒃𝒐𝒕 💕\n\n"
        f"𖥔 Choose an option below:"
    )
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ 𝐓𝐚𝐥𝐤 𝐭𝐨 𝑩𝒂𝒌𝒂 💬", callback_data="talk_info")],
        [InlineKeyboardButton("✨ 𝑭𝒓𝒊𝒆𝒏𝒅𝒔 🧸", url="https://t.me/ShreyaBotSupport"),
         InlineKeyboardButton("✨ 𝑮𝒂𝒎𝒆𝒔 🎮", callback_data="games_info")],
        [InlineKeyboardButton("➕ Add me to your group 👥", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
    ])
    await message.reply_text(text=txt, reply_markup=buttons)

@app.on_message(filters.command("status"))
async def status_cmd(client, message: Message):
    start = time.time()
    msg = await message.reply_text("🔄 Checking system...")
    end = time.time()
    ping = int((end - start) * 1000)
    
    # DB Check
    try:
        await users_col.find_one({"_id": OWNER_ID})
        db_status = "✅ Connected"
    except:
        db_status = "❌ Disconnected"
        
    txt = (
        "🤖 **System Status**\n\n"
        f"📶 **Ping:** `{ping}ms`\n"
        f"🗄️ **Database:** {db_status}\n"
        f"🧠 **AI Engine:** GitHub (GPT-4o) + Pollinations\n"
        f"👑 **Owner:** [{OWNER_ID}](tg://user?id={OWNER_ID})"
    )
    await msg.edit_text(txt)

# ---------------- 3. ECONOMY SYSTEM ---------------- #

@app.on_message(filters.command("daily"))
async def daily_cmd(client, message: Message):
    user = await get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    if now - user['last_daily'] < 86400:
        return await message.reply_text("⏳ Please wait 24 hours!")
        
    reward = 2000 if user['premium'] else 1000
    new_bal = user['balance'] + reward
    await update_user(user['_id'], {"balance": new_bal, "last_daily": now})
    
    txt = f"✅ You received: ${reward} daily reward! (Premium 🌟)" if user['premium'] else f"✅ You received: ${reward}!\n💓 Upgrade to Premium for $2000 daily!"
    await message.reply_text(txt)

@app.on_message(filters.command("bal"))
async def bal_cmd(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    data = await get_user(target.id, target.first_name)
    badge = "💖" if data['premium'] else "👤"
    
    txt = (
        f"{badge} **Name:** {data['name']}\n"
        f"💰 **Balance:** ${data['balance']}\n"
        f"❤️ **Status:** {data['status']}\n"
        f"⚔️ **Kills:** {data['kills']}"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("rob"))
async def rob_cmd(client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to a user!")
    
    robber = await get_user(message.from_user.id)
    victim = await get_user(message.reply_to_message.from_user.id)
    
    if robber['status'] == "dead": return await message.reply_text("You are dead! ☠️")
    if victim['status'] == "dead": return await message.reply_text("Already dead ☠️")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ Protected!")
    
    max_limit = 100000 if robber['premium'] else 10000
    try: amount = int(message.command[1])
    except: amount = random.randint(100, max_limit)
    
    if amount > max_limit: amount = max_limit
    if victim['balance'] < amount: amount = victim['balance']
    if amount <= 0: return await message.reply_text("They are broke! 🥺")
    
    if random.choice([True, False]):
        await update_user(victim['_id'], {"balance": victim['balance'] - amount})
        await update_user(robber['_id'], {"balance": robber['balance'] + amount})
        await message.reply_text(f"💸 You stole **${amount}**!")
    else:
        fine = 500
        await update_user(robber['_id'], {"balance": robber['balance'] - fine})
        await message.reply_text(f"🚔 Police caught you! Fined **${fine}**.")

@app.on_message(filters.command("give"))
async def give_cmd(client, message: Message):
    if not message.reply_to_message: return
    try: amount = int(message.command[1])
    except: return await message.reply_text("Usage: /give amount")
    
    sender = await get_user(message.from_user.id)
    receiver = await get_user(message.reply_to_message.from_user.id)
    
    if sender['balance'] < amount: return await message.reply_text("❌ Insufficient funds.")
    tax = int(amount * (0.05 if sender['premium'] else 0.10))
    
    await update_user(sender['_id'], {"balance": sender['balance'] - amount})
    await update_user(receiver['_id'], {"balance": receiver['balance'] + (amount - tax)})
    await message.reply_text(f"💸 Sent ${amount-tax} (Tax: ${tax})")

@app.on_message(filters.command("protect"))
async def protect_cmd(client, message: Message):
    if len(message.command) < 2: return await message.reply_text("Usage: /protect 1d")
    duration = message.command[1]
    days_map = {"1d": 1, "2d": 2, "3d": 3}
    if duration not in days_map: return
    
    user = await get_user(message.from_user.id)
    if days_map[duration] > 1 and not user['premium']: return await message.reply_text("❌ 2d/3d is for Premium users only!")
    cost = 2000 * days_map[duration]
    
    if user['balance'] < cost: return await message.reply_text(f"❌ Cost is ${cost}!")
    
    await update_user(user['_id'], {"balance": user['balance'] - cost, "protected_until": time.time() + (86400 * days_map[duration])})
    await message.reply_text(f"🛡️ Protected for {duration}!")

@app.on_message(filters.command("kill"))
async def kill_cmd(client, message: Message):
    if not message.reply_to_message: return
    killer = await get_user(message.from_user.id)
    victim = await get_user(message.reply_to_message.from_user.id)
    
    if killer['status'] == "dead": return await message.reply_text("You are dead!")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ Protected!")
    
    await update_user(victim['_id'], {"status": "dead"})
    await update_user(killer['_id'], {"kills": killer['kills'] + 1})
    await message.reply_text("🔪 Killed successfully!")

@app.on_message(filters.command("revive"))
async def revive_cmd(client, message: Message):
    target_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    payer = await get_user(message.from_user.id)
    if payer['balance'] < 500: return await message.reply_text("❌ Need $500!")
    
    await update_user(payer['_id'], {"balance": payer['balance'] - 500})
    await update_user(target_id, {"status": "alive"})
    await message.reply_text("❤️ Revived!")

@app.on_message(filters.command("toprich"))
async def toprich(client, message: Message):
    top = users_col.find().sort("balance", -1).limit(10)
    txt = "🏆 **Top Richest Users**\n\n"
    i = 1
    async for u in top:
        txt += f"{i}. {u['name']} - ${u['balance']}\n"
        i += 1
    await message.reply_text(txt)

# ---------------- 4. ADMIN DOT COMMANDS (FIXED) ---------------- #

async def check_admin(message):
    try:
        mem = await message.chat.get_member(message.from_user.id)
        return mem.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

@app.on_message(filters.command("ban", prefixes=".") & filters.group)
async def ban_user(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    try:
        await client.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        await message.reply_text("🚫 Banned!")
    except: await message.reply_text("❌ Failed.")

@app.on_message(filters.command("mute", prefixes=".") & filters.group)
async def mute_user(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    try:
        await client.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=False))
        await message.reply_text("🤐 Muted!")
    except: pass

@app.on_message(filters.command("pin", prefixes=".") & filters.group)
async def pin_msg(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    try: await message.reply_to_message.pin()
    except: pass

@app.on_message(filters.command("promote", prefixes=".") & filters.group)
async def promote_usr(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    try:
        await client.promote_chat_member(message.chat.id, message.reply_to_message.from_user.id, privileges=ChatPermissions(can_change_info=True, can_delete_messages=True, can_invite_users=True, can_restrict_members=True, can_pin_messages=True))
        await message.reply_text("👮‍♂️ Promoted to Admin!")
    except: pass

# ---------------- 5. OWNER / SUDO COMMANDS ---------------- #

@app.on_message(filters.command("sudo") & filters.user(OWNER_ID))
async def sudo_menu(client, message: Message):
    txt = (
        "👑 **Owner Commands (Hidden)**\n\n"
        "• /makepremium [id] - Give Premium\n"
        "• /removepremium [id] - Remove Premium\n"
        "• /premiumlist - List Premium Users\n"
        "• /broadcast [reply/text] - Send msg to all users\n"
        "• /status - Check system health"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text("Usage: Reply to msg or give text.")
    
    msg = await message.reply_text("📣 Broadcasting started...")
    users = users_col.find()
    sent = 0
    
    async for u in users:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy(u['_id'])
            else:
                await client.send_message(u['_id'], message.text.split(None, 1)[1])
            sent += 1
        except: pass # User blocked bot
        
    await msg.edit_text(f"✅ Broadcast complete! Sent to {sent} users.")

@app.on_message(filters.command("makepremium") & filters.user(OWNER_ID))
async def makepremium(client, message: Message):
    try:
        uid = int(message.command[1])
        await update_user(uid, {"premium": True})
        await message.reply_text(f"✅ User {uid} is now Premium!")
    except: pass

@app.on_message(filters.command("premiumlist") & filters.user(OWNER_ID))
async def premlist(client, message: Message):
    users = users_col.find({"premium": True})
    txt = "📋 **Premium Users**\n\n"
    async for u in users: txt += f"• `{u['_id']}` ({u['name']})\n"
    await message.reply_text(txt)

# ---------------- 6. GROUP LOGGER ---------------- #

@app.on_message(filters.new_chat_members)
async def new_group_log(client, message: Message):
    for member in message.new_chat_members:
        if member.id == client.me.id:
            # Bot added to group
            link = "No Link (Bot not Admin)"
            try:
                link = await client.export_chat_invite_link(message.chat.id)
            except: pass
            
            log = (
                f"📂 **Bot Added to Group**\n\n"
                f"🏷️ **Name:** {message.chat.title}\n"
                f"🆔 **ID:** `{message.chat.id}`\n"
                f"🔗 **Link:** {link}\n"
                f"👤 **Added By:** {message.from_user.mention}"
            )
            await log_event(log)

# ---------------- 7. STARTUP ---------------- #

async def main():
    print("Bot Starting...")
    await app.start()
    await app.set_bot_commands([
        BotCommand("start", "Start Bot"),
        BotCommand("help", "Admin Commands"),
        BotCommand("economy", "Economy Guide"),
        BotCommand("daily", "Claim Reward"),
        BotCommand("bal", "Check Balance"),
        BotCommand("pay", "Get Premium"),
        BotCommand("status", "System Health"),
    ])
    print("Bot is Alive!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
