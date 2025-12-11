import os
import time
import random
import asyncio
import requests
import urllib.parse
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatType, ChatAction, ChatMemberStatus
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
    print("❌ CRITICAL ERROR: MONGO_URL is missing! Commands will fail.")
    
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot
users_col = db.users

# --- Database Helper Functions ---
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
        except Exception as e:
            print(f"Log Error: {e}")

# ---------------- 1. EXACT TEXT MENUS (RESTORED) ---------------- #

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    # Register User
    await get_user(message.from_user.id, message.from_user.first_name)
    
    # Logger (Only in PM)
    if message.chat.type == ChatType.PRIVATE:
        log_txt = (
            f"🚀 **New User Started Bot**\n\n"
            f"👤 **User:** [{message.from_user.first_name}](tg://user?id={message.from_user.id})\n"
            f"🆔 **ID:** `{message.from_user.id}`"
        )
        await log_event(log_txt)

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

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    if query.data == "talk_info":
        await query.answer()
        await query.message.reply_text("To talk to me, just send me any message 💬✨")
    elif query.data == "games_info":
        await query.answer("Use /economy to see games! 🎮", show_alert=True)

@app.on_message(filters.command("economy"))
async def economy_command(client, message: Message):
    txt = (
        "💰 **Baka Economy System Guide**\n\n"
        "💬 **How it works:**\n"
        "Manage your virtual money and items in the group! Use commands below to earn, gift, buy, or interact with others.\n\n"
        "🔹 **Normal Users (👤):**\n"
        "• /daily — Receive $1000 daily reward\n"
        "• /claim — Add Baka in group to claim 10k+\n"
        "• /bal — Check your/your friend's balance (👤 prefix)\n"
        "• /rob (reply) amount — Max $10k\n"
        "• /kill (reply) — Reward $100-200\n"
        "• /revive (reply or without reply) — Revive you or a friend\n"
        "• /protect 1d — Buy protection\n"
        "• /give (reply) amount — Gift money (10% fee)\n"
        "• /toprich — See top 10 richest users (👤 normal)\n"
        "• /topkill — See top 10 killers (👤 normal)\n\n"
        "🔹 **Premium Users (💖):**\n"
        "• /pay — Become premium user ($50k)\n"
        "• /daily — Receive $2000 daily reward\n"
        "• /rob (reply) — Max $100,000\n"
        "• /kill (reply) — Reward $200-400\n"
        "• /protect 1d|2d|3d — Buy protection (avoid robbery)"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    txt = (
        "🛡️ **Admin Commands (.prefix only):**\n"
        ".warn [reply] - Warn a user (3 = ban)\n"
        ".mute [reply] - Mute user\n"
        ".unmute [reply] - Unmute user\n"
        ".ban [reply] - Ban user\n"
        ".unban [reply] - Unban user\n"
        ".pin [reply] - Pin a message\n"
        ".del - delete a message\n\n"
        "🎮 **Game Features**\n"
        "To know about the Economy System, tap /economy\n\n"
        "Have fun and be lucky 🍀"
    )
    await message.reply_text(txt)

# ---------------- 2. ECONOMY COMMANDS (RESTORED) ---------------- #

@app.on_message(filters.command("daily"))
async def daily_cmd(client, message: Message):
    user = await get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    
    if now - user['last_daily'] < 86400:
        remaining = int((86400 - (now - user['last_daily'])) / 3600)
        return await message.reply_text(f"⏳ Please wait {remaining} hours!")
        
    reward = 2000 if user['premium'] else 1000
    await update_user(user['_id'], {"balance": user['balance'] + reward, "last_daily": now})
    
    if user['premium']:
        await message.reply_text(f"✅ You received: ${reward} daily reward! (Premium 🌟)")
    else:
        await message.reply_text(f"✅ You received: ${reward} daily reward!\n💓 Upgrade to premium using /pay to get $2000 daily reward!")

@app.on_message(filters.command("bal"))
async def bal_cmd(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    data = await get_user(target.id, target.first_name)
    badge = "💖" if data['premium'] else "👤"
    
    txt = (
        f"{badge} Name: {data['name']}\n"
        f"💰 Total Balance: ${data['balance']}\n"
        f"❤️ Status: {data['status']}\n"
        f"⚔️ Kills: {data['kills']}"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("rob"))
async def rob_cmd(client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to a user to rob them!")
    
    robber = await get_user(message.from_user.id)
    victim = await get_user(message.reply_to_message.from_user.id)
    
    if robber['status'] == "dead": return await message.reply_text("You are dead! ☠️")
    if victim['status'] == "dead": return await message.reply_text("They are already dead ☠️")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ This user is protected!")
    
    max_limit = 100000 if robber['premium'] else 10000
    try: amount = int(message.command[1])
    except: amount = random.randint(100, max_limit)
    
    if amount > max_limit: amount = max_limit
    if victim['balance'] < amount: amount = victim['balance']
    
    if amount <= 0: return await message.reply_text("They have no money! 🥺")
    
    if random.choice([True, False]):
        await update_user(victim['_id'], {"balance": victim['balance'] - amount})
        await update_user(robber['_id'], {"balance": robber['balance'] + amount})
        await message.reply_text(f"💸 **Success!** You stole **${amount}** from {message.reply_to_message.from_user.first_name}!")
    else:
        fine = 500
        await update_user(robber['_id'], {"balance": robber['balance'] - fine})
        await message.reply_text(f"🚔 **Caught!** Police fined you **${fine}**.")

@app.on_message(filters.command("kill"))
async def kill_cmd(client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to someone! 😈")
    killer = await get_user(message.from_user.id)
    victim = await get_user(message.reply_to_message.from_user.id)
    
    if killer['status'] == "dead": return await message.reply_text("You are dead! /revive first.")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ They are protected!")
    
    await update_user(victim['_id'], {"status": "dead"})
    await update_user(killer['_id'], {"kills": killer['kills'] + 1})
    await message.reply_text(f"⚠️ You killed {message.reply_to_message.from_user.first_name}!\nThey are now dead.")

@app.on_message(filters.command("revive"))
async def revive_cmd(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    payer = await get_user(message.from_user.id)
    
    if payer['balance'] < 500: return await message.reply_text("❌ You need $500!")
    await update_user(payer['_id'], {"balance": payer['balance'] - 500})
    await update_user(target.id, {"status": "alive"})
    await message.reply_text("❤️ Revived!")

@app.on_message(filters.command("protect"))
async def protect_cmd(client, message: Message):
    if len(message.command) < 2: return await message.reply_text("⚠️ Usage: /protect 1d")
    duration = message.command[1]
    days_map = {"1d": 1, "2d": 2, "3d": 3}
    if duration not in days_map: return
    
    user = await get_user(message.from_user.id)
    if days_map[duration] > 1 and not user['premium']: return await message.reply_text("❌ Premium only!")
    
    cost = 2000 * days_map[duration]
    if user['balance'] < cost: return await message.reply_text(f"❌ You need ${cost}!")
    
    await update_user(user['_id'], {"balance": user['balance'] - cost, "protected_until": time.time() + (86400 * days_map[duration])})
    await message.reply_text(f"🛡️ Protected for {duration}!")

@app.on_message(filters.command("pay"))
async def pay_cmd(client, message: Message):
    txt = (
        "💓 **Baka Premium Access Link**\n\n"
        "👇 **Important Note :**\n"
        "1. You must enter your Telegram ID (Numeric ID) on the payment page.\n"
        "2. Upon successful payment, you will receive automatic premium access.\n\n"
        "Thank you! 💓\n\n\n"
        "Here is your payment link: @WTF_Phantom"
    )
    await message.reply_text(txt)

# ---------------- 3. ADMIN DOT COMMANDS (FIXED) ---------------- #

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

@app.on_message(filters.command("unmute", prefixes=".") & filters.group)
async def unmute_user(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    try:
        await client.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=True))
        await message.reply_text("🗣️ Unmuted!")
    except: pass

@app.on_message(filters.command("pin", prefixes=".") & filters.group)
async def pin_msg(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    try: await message.reply_to_message.pin()
    except: pass

# ---------------- 4. OWNER / SUDO COMMANDS ---------------- #

@app.on_message(filters.command("sudo") & filters.user(OWNER_ID))
async def sudo_menu(client, message: Message):
    txt = (
        "👑 **Owner Commands**\n\n"
        "• /makepremium [id]\n"
        "• /removepremium [id]\n"
        "• /broadcast [reply/text]\n"
        "• /status"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(client, message: Message):
    if not message.reply_to_message and len(message.command) < 2: return
    msg = await message.reply_text("📣 Broadcasting...")
    
    users = users_col.find()
    count = 0
    async for u in users:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy(u['_id'])
            else:
                await client.send_message(u['_id'], message.text.split(None, 1)[1])
            count += 1
        except: pass
    await msg.edit_text(f"✅ Sent to {count} users.")

@app.on_message(filters.command("makepremium") & filters.user(OWNER_ID))
async def makepremium(client, message: Message):
    try:
        uid = int(message.command[1])
        await update_user(uid, {"premium": True})
        await message.reply_text(f"✅ User {uid} is Premium!")
    except: pass

@app.on_message(filters.command("status"))
async def status_cmd(client, message: Message):
    start = time.time()
    msg = await message.reply_text("Checking...")
    ping = int((time.time() - start) * 1000)
    await msg.edit_text(f"📶 **Ping:** `{ping}ms`\n✅ **System:** Online")

# ---------------- 5. DUAL AI ENGINE (GitHub + Pollinations) ---------------- #

def ai_github(text):
    if not GITHUB_TOKEN: return None
    try:
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GITHUB_TOKEN}"}
        payload = {
            "messages": [{"role": "system", "content": "You are Baka, a sassy female bot. Reply in Hinglish (Hindi+English). Be savage, cute."}, {"role": "user", "content": text}],
            "model": "gpt-4o", "temperature": 0.8, "max_tokens": 200
        }
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200: return res.json()["choices"][0]["message"]["content"]
    except: pass
    return None

def ai_pollinations(text):
    try:
        seed = random.randint(1, 9999)
        system = "You are Baka, a sassy female bot. Reply in Hinglish. Be savage, cute."
        encoded = urllib.parse.quote(f"{system} {text}")
        res = requests.get(f"https://text.pollinations.ai/{encoded}?seed={seed}&model=openai", timeout=8)
        if res.status_code == 200: return res.text
    except: pass
    return None

@app.on_message(filters.text)
async def chat_handler(client, message: Message):
    if message.text.startswith("/") or message.text.startswith("."): return
    
    is_private = message.chat.type == ChatType.PRIVATE
    is_mentioned = message.mentioned
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == client.me.id
    
    if is_private or is_mentioned or is_reply:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # 1. Try GitHub
        reply = await asyncio.to_thread(ai_github, message.text)
        
        # 2. Fallback Pollinations
        if not reply:
            reply = await asyncio.to_thread(ai_pollinations, message.text)
            
        await message.reply_text(reply if reply else "Server busy... 😵‍💫")

# ---------------- 6. GROUP LOGGER ---------------- #

@app.on_message(filters.new_chat_members)
async def new_group_log(client, message: Message):
    for member in message.new_chat_members:
        if member.id == client.me.id:
            await log_event(f"📂 **Bot Added to Group**\n🏷️ **Title:** {message.chat.title}\n🆔 **ID:** `{message.chat.id}`\n👤 **By:** {message.from_user.mention}")

# ---------------- 7. STARTUP ---------------- #

async def main():
    print("Bot Starting...")
    async with app:
        # LOG DEPLOYMENT
        await log_event("✅ **Bot Deployed Successfully!**\n📅 System: Online\n🤖 Version: Ultimate v1.0")
        
        await app.set_bot_commands([
            BotCommand("start", "Start Bot"),
            BotCommand("help", "Help Menu"),
            BotCommand("economy", "Economy Guide"),
            BotCommand("daily", "Claim Reward"),
            BotCommand("bal", "Check Balance"),
            BotCommand("pay", "Buy Premium"),
            BotCommand("status", "System Status"),
        ])
        print("Bot is Alive!")
        await idle()

if __name__ == "__main__":
    app.run(main())
