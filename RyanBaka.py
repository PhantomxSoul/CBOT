import os
import time
import random
import asyncio
import requests
import urllib.parse
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatType, ChatAction, ChatMemberStatus
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Message, 
    CallbackQuery, 
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

# ---------------- DATABASE ---------------- #
if not MONGO_URL:
    print("❌ CRITICAL: MONGO_URL MISSING")
    exit()

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot
users_col = db.users

async def get_user(user_id, name="User"):
    user = await users_col.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id, "name": name, "balance": 0, "status": "alive",
            "kills": 0, "premium": False, "last_daily": 0, "protected_until": 0,
            "items": []
        }
        await users_col.insert_one(user)
    return user

async def update_user(user_id, data):
    await users_col.update_one({"_id": user_id}, {"$set": data})

async def log_event(text):
    if LOG_CHANNEL_ID != 0:
        try: await app.send_message(LOG_CHANNEL_ID, text, disable_web_page_preview=True)
        except: pass

# ---------------- 1. CORE MENUS (EXACT CLONE) ---------------- #

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await get_user(message.from_user.id, message.from_user.first_name)
    
    # Logger
    if message.chat.type == ChatType.PRIVATE:
        await log_event(f"🚀 **User Started Bot**\n👤 [{message.from_user.first_name}](tg://user?id={message.from_user.id}) (`{message.from_user.id}`)")

    txt = (
        f"✨ 𝐇𝐞𝐲 ◄❥͜͡⃟💔꯭᪳𝄄─𝐃꯭𝐄꯭𝐀꯭𝐃<꯭/꯭᪵>𝐔꯭𝐒𝐄꯭𝐑─𝄄꯭➤⃝ ⃝⃪⃕☠️ ~\n"
        f"𖦹 𝒀𝒐𝒖'𝒓𝒆 𝒕𝒂𝒍𝒌𝒊𝒏𝒈 𝒕𝒐 𝑩𝒂𝒌𝒂, 𝒂 𝒔𝒂𝒔𝒔𝒚 𝒄𝒖𝒕𝒊𝒆 𝒃𝒐𝒕 💕\n\n"
        f"𖥔 Choose an option below:"
    )
    # Using your exact requested buttons
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Talk to Baka 💬", callback_data="talk_info")],
        [InlineKeyboardButton("✨ Friends 🧸", url="https://t.me/ShreyaBotSupport"),
         InlineKeyboardButton("✨ Games 🎮", callback_data="games_info")],
        [InlineKeyboardButton("➕ Add me to your group 👥", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
    ])
    await message.reply_text(text=txt, reply_markup=buttons)

@app.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    if query.data == "talk_info":
        await query.answer()
        await query.message.reply_text("To talk to me, just send me any message 💬✨")
    elif query.data == "games_info":
        await query.answer("Use /economy to see games! 🎮", show_alert=True)

@app.on_message(filters.command("help"))
async def help_cmd(client, message: Message):
    txt = (
        "🛡️ **Admin Commands (.prefix only):**\n"
        ".warn [reply] - Warn a user (3 = ban)\n"
        ".unwarn [reply] - Remove 1 warning\n"
        ".mute [reply] - Mute temporarily/permanently\n"
        ".unmute [reply] - Unmute the user\n"
        ".ban [reply] - Ban user\n"
        ".unban [reply] - Unban user\n"
        ".kick [reply] - Kick from group\n"
        ".promote [reply] 1/2/3 - Promote user\n"
        ".demote [reply] - Demote admin\n"
        ".pin [reply] - Pin a message\n"
        ".unpin - Unpin current message\n"
        ".del - Delete a message\n"
        ".help - Show this help\n\n"
        "To talk to me, just send me any message 💬✨\n\n"
        "🎮 **Game Features**\n"
        "To know about the Economy System, tap /economy\n\n"
        "Have fun and be lucky 🍀"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("economy"))
async def economy_cmd(client, message: Message):
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
        "• /protect 1d|2d|3d — Buy protection\n"
        "• /check — Check protection status"
    )
    await message.reply_text(txt)

# ---------------- 2. ECONOMY COMMANDS ---------------- #

@app.on_message(filters.command("daily"))
async def daily(client, message: Message):
    user = await get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    if now - user['last_daily'] < 86400:
        return await message.reply_text("⏳ Please wait 24 hours!")
    reward = 2000 if user['premium'] else 1000
    await update_user(user['_id'], {"balance": user['balance'] + reward, "last_daily": now})
    await message.reply_text(f"✅ You received: ${reward} daily reward!")

@app.on_message(filters.command("bal"))
async def bal(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    data = await get_user(target.id, target.first_name)
    badge = "💖" if data['premium'] else "👤"
    await message.reply_text(f"{badge} **Name:** {data['name']}\n💰 **Balance:** ${data['balance']}\n❤️ **Status:** {data['status']}\n⚔️ **Kills:** {data['kills']}")

@app.on_message(filters.command("rob"))
async def rob(client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to someone!")
    robber = await get_user(message.from_user.id)
    victim = await get_user(message.reply_to_message.from_user.id)
    
    if robber['status'] == "dead": return await message.reply_text("You are dead ☠️")
    if victim['status'] == "dead": return await message.reply_text("They are already dead ☠️")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ Protected!")
    
    limit = 100000 if robber['premium'] else 10000
    try: amt = int(message.command[1])
    except: amt = random.randint(100, limit)
    if amt > limit: amt = limit
    if victim['balance'] < amt: amt = victim['balance']
    
    if amt <= 0: return await message.reply_text("They are broke!")
    
    if random.choice([True, False]):
        await update_user(victim['_id'], {"balance": victim['balance'] - amt})
        await update_user(robber['_id'], {"balance": robber['balance'] + amt})
        await message.reply_text(f"💸 Stole **${amt}**!")
    else:
        fine = 500
        await update_user(robber['_id'], {"balance": robber['balance'] - fine})
        await message.reply_text(f"🚔 Caught! Fined ${fine}.")

@app.on_message(filters.command("kill"))
async def kill(client, message: Message):
    if not message.reply_to_message: return
    killer = await get_user(message.from_user.id)
    victim = await get_user(message.reply_to_message.from_user.id)
    if killer['status'] == "dead": return await message.reply_text("You are dead!")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ Protected!")
    await update_user(victim['_id'], {"status": "dead"})
    await update_user(killer['_id'], {"kills": killer['kills'] + 1})
    await message.reply_text("🔪 Killed successfully!")

@app.on_message(filters.command("revive"))
async def revive(client, message: Message):
    payer = await get_user(message.from_user.id)
    target_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    if payer['balance'] < 500: return await message.reply_text("❌ Need $500!")
    await update_user(payer['_id'], {"balance": payer['balance'] - 500})
    await update_user(target_id, {"status": "alive"})
    await message.reply_text("❤️ Revived!")

@app.on_message(filters.command("protect"))
async def protect(client, message: Message):
    if len(message.command) < 2: return await message.reply_text("Usage: /protect 1d")
    days = {"1d": 1, "2d": 2, "3d": 3}.get(message.command[1])
    if not days: return
    user = await get_user(message.from_user.id)
    if days > 1 and not user['premium']: return await message.reply_text("❌ 2d/3d is for Premium!")
    cost = 2000 * days
    if user['balance'] < cost: return await message.reply_text(f"❌ Cost: ${cost}")
    await update_user(user['_id'], {"balance": user['balance'] - cost, "protected_until": time.time() + (86400 * days)})
    await message.reply_text(f"🛡️ Protected for {message.command[1]}!")

@app.on_message(filters.command("give"))
async def give(client, message: Message):
    if not message.reply_to_message: return
    try: amt = int(message.command[1])
    except: return await message.reply_text("Usage: /give [amount]")
    sender = await get_user(message.from_user.id)
    if sender['balance'] < amt: return await message.reply_text("❌ Low balance.")
    rec = await get_user(message.reply_to_message.from_user.id)
    tax = int(amt * (0.05 if sender['premium'] else 0.10))
    await update_user(sender['_id'], {"balance": sender['balance'] - amt})
    await update_user(rec['_id'], {"balance": rec['balance'] + (amt - tax)})
    await message.reply_text(f"💸 Sent ${amt-tax} (Tax: ${tax})")

@app.on_message(filters.command("toprich"))
async def toprich(client, message: Message):
    top = users_col.find().sort("balance", -1).limit(10)
    txt = "🏆 **Top Richest**\n\n"
    i = 1
    async for u in top:
        txt += f"{i}. {u['name']} - ${u['balance']}\n"
        i += 1
    await message.reply_text(txt)

@app.on_message(filters.command("check"))
async def check_prot(client, message: Message):
    user = await get_user(message.from_user.id)
    rem = user['protected_until'] - time.time()
    if rem > 0: await message.reply_text(f"🛡️ Protected for {int(rem/3600)} hours.")
    else: await message.reply_text("🛡️ No protection active.")

@app.on_message(filters.command("claim") & filters.group)
async def claim(client, message: Message):
    user = await get_user(message.from_user.id)
    if user['claimed_group']: return await message.reply_text("Already claimed!")
    await update_user(user['_id'], {"balance": user['balance'] + 10000, "claimed_group": True})
    await message.reply_text("🎉 Claimed $10,000!")

@app.on_message(filters.command("topkill"))
async def topkill(client, message: Message):
    top = users_col.find().sort("kills", -1).limit(10)
    txt = "⚔️ **Top Killers**\n\n"
    i = 1
    async for u in top:
        txt += f"{i}. {u['name']} - {u['kills']} Kills\n"
        i += 1
    await message.reply_text(txt)

# ---------------- 3. FUN & INTERACTION COMMANDS ---------------- #

@app.on_message(filters.command(["slap", "punch", "kill", "bite", "kiss", "hug", "kick"]))
async def interaction(client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to someone!")
    act = message.command[0]
    acts = {
        "slap": "slapped 👋", "punch": "punched 👊", "bite": "bit 🦷",
        "kiss": "kissed 💋", "hug": "hugged 🤗", "kick": "kicked 🦶"
    }
    await message.reply_text(f"{message.from_user.mention} {acts.get(act, 'poked')} {message.reply_to_message.from_user.mention}!")

@app.on_message(filters.command(["truth", "dare", "puzzle"]))
async def games(client, message: Message):
    cmd = message.command[0]
    if cmd == "truth": t = random.choice(["What is your biggest fear?", "Who is your crush?"])
    elif cmd == "dare": t = random.choice(["Send a voice note singing.", "Change your DP for 1 hour."])
    else: t = random.choice(["What has keys but can't open locks? (Piano)", "I speak without a mouth. What am I? (Echo)"])
    await message.reply_text(f"🎲 **{cmd.title()}:** {t}")

@app.on_message(filters.command(["couples", "love", "crush"]))
async def couples(client, message: Message):
    if message.chat.type == ChatType.PRIVATE: return await message.reply_text("Only in groups!")
    await message.reply_text(f"💘 **Match of the day:** {message.from_user.mention} ❤️ {message.from_user.mention}!")

@app.on_message(filters.command("music"))
async def music(client, message: Message):
    await message.reply_text("🎶 **Random Music:**\n1. Blinding Lights\n2. Stay\n3. Levitating")

@app.on_message(filters.command("tr"))
async def translate(client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to a message to translate!")
    # Use AI for translation
    res = await asyncio.to_thread(ai_github, f"Translate this to English: {message.reply_to_message.text}")
    await message.reply_text(f"🔤 **Translation:**\n{res}")

@app.on_message(filters.command("id"))
async def id_cmd(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    await message.reply_text(f"🆔 **ID:** `{target.id}`")

@app.on_message(filters.command("adminlist"))
async def adminlist(client, message: Message):
    if message.chat.type == ChatType.PRIVATE: return
    admins = []
    async for m in client.get_chat_members(message.chat.id, filter=ChatMemberStatus.ADMINISTRATOR):
        admins.append(m.user.mention)
    await message.reply_text("👮‍♂️ **Admins:**\n" + "\n".join(admins))

@app.on_message(filters.command("owner"))
async def tag_owner(client, message: Message):
    if message.chat.type == ChatType.PRIVATE: return
    async for m in client.get_chat_members(message.chat.id, filter=ChatMemberStatus.OWNER):
        await message.reply_text(f"👑 **Owner:** {m.user.mention}")

# ---------------- 4. ADMIN COMMANDS (DOT PREFIX) ---------------- #

async def check_admin(message):
    try:
        mem = await message.chat.get_member(message.from_user.id)
        return mem.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

@app.on_message(filters.command(["ban", "unban", "kick", "mute", "unmute", "pin", "unpin", "demote"], prefixes=".") & filters.group)
async def admin_actions(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    cmd = message.command[0]
    user = message.reply_to_message.from_user
    try:
        if cmd == "ban":
            await client.ban_chat_member(message.chat.id, user.id)
            await message.reply_text(f"🚫 Banned {user.mention}")
        elif cmd == "kick":
            await client.ban_chat_member(message.chat.id, user.id)
            await client.unban_chat_member(message.chat.id, user.id)
            await message.reply_text(f"👢 Kicked {user.mention}")
        elif cmd == "mute":
            await client.restrict_chat_member(message.chat.id, user.id, ChatPermissions(can_send_messages=False))
            await message.reply_text(f"🤐 Muted {user.mention}")
        elif cmd == "unmute":
            await client.restrict_chat_member(message.chat.id, user.id, ChatPermissions(can_send_messages=True))
            await message.reply_text(f"🗣️ Unmuted {user.mention}")
        elif cmd == "pin":
            await message.reply_to_message.pin()
        elif cmd == "unpin":
            await message.reply_to_message.unpin()
    except Exception as e:
        await message.reply_text("❌ Error: I need Admin Rights!")

# ---------------- 5. SUDO & SYSTEM ---------------- #

@app.on_message(filters.command("sudo") & filters.user(OWNER_ID))
async def sudo(client, message: Message):
    txt = (
        "👑 **Owner Commands**\n"
        "/makepremium [id]\n/removepremium [id]\n/premiumlist\n/broadcast [reply]\n/status"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("status"))
async def status(client, message: Message):
    # Works for everyone now
    start = time.time()
    msg = await message.reply_text("Checking...")
    ping = int((time.time() - start) * 1000)
    await msg.edit_text(f"📶 **Ping:** `{ping}ms`\n✅ **System:** Online\n🤖 **AI:** Dual-Core")

@app.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast(client, message: Message):
    if not message.reply_to_message: return
    msg = await message.reply_text("📣 Broadcasting...")
    users = users_col.find()
    c = 0
    async for u in users:
        try:
            await message.reply_to_message.copy(u['_id'])
            c += 1
        except: pass
    await msg.edit_text(f"✅ Sent to {c} users.")

@app.on_message(filters.command("premiumlist") & filters.user(OWNER_ID))
async def premlist(client, message: Message):
    users = users_col.find({"premium": True})
    t = "📋 **Premiums:**\n"
    async for u in users: t += f"`{u['_id']}`\n"
    await message.reply_text(t)

@app.on_message(filters.command("makepremium") & filters.user(OWNER_ID))
async def addprem(client, message: Message):
    try:
        await update_user(int(message.command[1]), {"premium": True})
        await message.reply_text("✅ Added!")
    except: pass

@app.on_message(filters.command("pay"))
async def pay(client, message: Message):
    await message.reply_text("💓 **Baka Premium Access Link**\n\n👇 **Important Note :**\n1. You must enter your Telegram ID (Numeric ID) on the payment page.\n2. Upon successful payment, you will receive automatic premium access.\n\nThank you! 💓\n\n\nHere is your payment link: @WTF_Phantom")

# ---------------- 6. AI ENGINE (DUAL CORE) ---------------- #

def ai_github(text):
    if not GITHUB_TOKEN: return None
    try:
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GITHUB_TOKEN}"}
        payload = {"messages": [{"role": "system", "content": "You are Baka, a sassy female bot. Reply in Hinglish. Be savage, cute."}, {"role": "user", "content": text}], "model": "gpt-4o", "temperature": 0.8}
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200: return res.json()["choices"][0]["message"]["content"]
    except: pass
    return None

def ai_pollinations(text):
    try:
        seed = random.randint(1, 9999)
        url = f"https://text.pollinations.ai/{urllib.parse.quote(text)}?seed={seed}&model=openai&system={urllib.parse.quote('You are Baka, sassy female bot in Hinglish.')}"
        res = requests.get(url, timeout=8)
        if res.status_code == 200: return res.text
    except: pass
    return None

@app.on_message(filters.text & ~filters.regex(r"^[/\.]"))
async def chat_handler(client, message: Message):
    is_p = message.chat.type == ChatType.PRIVATE
    is_m = message.mentioned
    is_r = message.reply_to_message and message.reply_to_message.from_user.id == client.me.id
    
    if is_p or is_m or is_r:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        res = await asyncio.to_thread(ai_github, message.text)
        if not res: res = await asyncio.to_thread(ai_pollinations, message.text)
        await message.reply_text(res if res else "Error 😵‍💫")

# ---------------- 7. STARTUP ---------------- #

async def main():
    print("Bot Starting...")
    await app.start()
    await log_event("✅ **Bot Deployed Successfully!**\n📅 System: Online\n🤖 Version: Ultimate Clone")
    
    # REGISTERING ALL COMMANDS FROM SCREENSHOTS
    await app.set_bot_commands([
        BotCommand("start", "Talk to Baka"),
        BotCommand("pay", "Buy premium access"),
        BotCommand("check", "Check protection"),
        BotCommand("daily", "Claim $1000 reward"),
        BotCommand("claim", "Add baka in groups and claim"),
        BotCommand("help", "Show admin commands"),
        BotCommand("economy", "See all economy commands"),
        BotCommand("bal", "see ur/ur friend's balance"),
        BotCommand("rob", "Reply to someone"),
        BotCommand("kill", "Reply to someone"),
        BotCommand("revive", "Use with or without reply"),
        BotCommand("protect", "Protect urself from robbery"),
        BotCommand("give", "Give money to replied user"),
        BotCommand("toprich", "See top 10 users"),
        BotCommand("topkill", "See top 10 killers"),
        BotCommand("kiss", "Reply to someone"),
        BotCommand("hug", "Reply to someone"),
        BotCommand("slap", "Reply to someone"),
        BotCommand("truth", "Picks a truth"),
        BotCommand("dare", "Picks a dare"),
        BotCommand("tr", "Translate any text"),
        BotCommand("adminlist", "Check adminlist"),
        BotCommand("owner", "Tag group owner"),
        BotCommand("status", "System Health"),
    ])
    print("Bot is Alive!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
