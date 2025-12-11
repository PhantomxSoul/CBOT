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

# --- ITEM SHOP DATA ---
SHOP_ITEMS = {
    "rose": {"name": "Rose", "emoji": "🌹", "cost": 500},
    "chocolate": {"name": "Chocolate", "emoji": "🍫", "cost": 800},
    "ring": {"name": "Ring", "emoji": "💍", "cost": 2000},
    "teddy": {"name": "Teddy Bear", "emoji": "🧸", "cost": 1500},
    "pizza": {"name": "Pizza", "emoji": "🍕", "cost": 600},
    "box": {"name": "Surprise Box", "emoji": "🎁", "cost": 2500},
    "puppy": {"name": "Puppy", "emoji": "🐶", "cost": 3000},
    "cake": {"name": "Cake", "emoji": "🎂", "cost": 1000},
    "letter": {"name": "Love Letter", "emoji": "💌", "cost": 400},
    "cat": {"name": "Cat", "emoji": "🐱", "cost": 2500},
}

async def get_user(user_id, name="User"):
    user = await users_col.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id, "name": name, "balance": 0, "status": "alive",
            "kills": 0, "premium": False, "last_daily": 0, "protected_until": 0,
            "items": {} # Stores items like {"rose": 1, "ring": 2}
        }
        await users_col.insert_one(user)
    return user

async def update_user(user_id, data):
    await users_col.update_one({"_id": user_id}, {"$set": data})

async def log_event(text):
    if LOG_CHANNEL_ID != 0:
        try: await app.send_message(LOG_CHANNEL_ID, text, disable_web_page_preview=True)
        except: pass

# ---------------- 1. MENUS & CORE ---------------- #

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await get_user(message.from_user.id, message.from_user.first_name)
    
    if message.chat.type == ChatType.PRIVATE:
        await log_event(f"🚀 **User Started Bot**\n👤 {message.from_user.mention} (`{message.from_user.id}`)")

    txt = (
        f"✨ 𝐇𝐞𝐲 {message.from_user.mention} ~\n"
        f"𖦹 𝒀𝒐𝒖'𝒓𝒆 𝒕𝒂𝒍𝒌𝒊𝒏𝒈 𝒕𝒐 𝑩𝒂𝒌𝒂, 𝒂 𝒔𝒂𝒔𝒔𝒚 𝒄𝒖𝒕𝒊𝒆 𝒃𝒐𝒕 💕\n\n"
        f"𖥔 Choose an option below:"
    )
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
        ".warn, .mute, .ban, .kick, .pin, .del\n\n"
        "🎮 **Features**\n"
        "Tap /economy for Money/Game commands."
    )
    await message.reply_text(txt)

@app.on_message(filters.command("economy"))
async def economy_cmd(client, message: Message):
    txt = (
        "💰 **Baka Economy System Guide**\n\n"
        "🔹 **Normal Users (👤):**\n"
        "/daily, /claim, /bal, /rob, /kill, /revive, /protect, /give\n"
        "/items, /gift, /toprich, /topkill\n\n"
        "🔹 **Premium Users (💖):**\n"
        "/pay, /daily ($2000), /rob ($100k limit), /check"
    )
    await message.reply_text(txt)

# ---------------- 2. ITEM SHOP LOGIC (NEW) ---------------- #

@app.on_message(filters.command("items"))
async def shop_list(client, message: Message):
    txt = "📦 **Available Gift Items:**\n\n"
    for key, item in SHOP_ITEMS.items():
        txt += f"{item['emoji']} **{item['name']}** — ${item['cost']}\n"
    await message.reply_text(txt)

@app.on_message(filters.command("item"))
async def my_items(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    user = await get_user(target.id, target.first_name)
    
    items = user.get("items", {})
    if not items:
        # EXACT TEXT FROM SCREENSHOT
        return await message.reply_text(f"{target.mention} has no items yet 😢")
    
    txt = f"🎒 **{target.first_name}'s Items:**\n\n"
    for key, count in items.items():
        if count > 0:
            meta = SHOP_ITEMS.get(key, {"name": key, "emoji": "❓"})
            txt += f"{meta['emoji']} **{meta['name']}**: {count}\n"
    await message.reply_text(txt)

@app.on_message(filters.command("gift"))
async def gift_item(client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to the user you want to gift!")
    
    try: item_name = message.command[1].lower()
    except: return await message.reply_text("Usage: /gift rose (Reply to user)")
    
    # Match item name (allow "teddy" for "Teddy Bear")
    item_key = None
    for k in SHOP_ITEMS:
        if k in item_name or item_name in k:
            item_key = k
            break
            
    if not item_key: return await message.reply_text("❌ Item not found! Check /items")
    
    sender = await get_user(message.from_user.id)
    receiver = await get_user(message.reply_to_message.from_user.id)
    cost = SHOP_ITEMS[item_key]["cost"]
    
    if sender['balance'] < cost:
        return await message.reply_text(f"❌ You need ${cost} to buy this!")
    
    # Transaction
    new_bal = sender['balance'] - cost
    # Update Receiver Inventory
    r_items = receiver.get("items", {})
    r_items[item_key] = r_items.get(item_key, 0) + 1
    
    await update_user(sender['_id'], {"balance": new_bal})
    await update_user(receiver['_id'], {"items": r_items})
    
    emoji = SHOP_ITEMS[item_key]["emoji"]
    name = SHOP_ITEMS[item_key]["name"]
    await message.reply_text(f"🎁 You gifted {emoji} **{name}** to {message.reply_to_message.from_user.mention}!")

# ---------------- 3. ECONOMY COMMANDS ---------------- #

@app.on_message(filters.command("revive"))
async def revive(client, message: Message):
    # Logic: If reply, revive target. If no reply, revive self.
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        target_user = message.from_user
        
    target_data = await get_user(target_user.id)
    payer_data = await get_user(message.from_user.id)
    
    # EXACT TEXT LOGIC
    if target_data['status'] == "alive":
        return await message.reply_text(f"✅ {target_user.mention} is already alive!")
        
    if payer_data['balance'] < 500:
        return await message.reply_text(f"❌ You need $500 to revive!")
        
    await update_user(payer_data['_id'], {"balance": payer_data['balance'] - 500})
    await update_user(target_data['_id'], {"status": "alive"})
    await message.reply_text(f"❤️ Revived {target_user.mention}! (-$500)")

@app.on_message(filters.command("daily"))
async def daily(client, message: Message):
    user = await get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    if now - user['last_daily'] < 86400: return await message.reply_text("⏳ Please wait 24 hours!")
    reward = 2000 if user['premium'] else 1000
    await update_user(user['_id'], {"balance": user['balance'] + reward, "last_daily": now})
    await message.reply_text(f"✅ Received ${reward}!")

@app.on_message(filters.command("bal"))
async def bal(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    data = await get_user(target.id, target.first_name)
    badge = "💖" if data['premium'] else "👤"
    await message.reply_text(f"{badge} **Name:** {data['name']}\n💰 **Balance:** ${data['balance']}\n❤️ **Status:** {data['status']}")

@app.on_message(filters.command("rob"))
async def rob(client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to someone!")
    robber, victim = await get_user(message.from_user.id), await get_user(message.reply_to_message.from_user.id)
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
    killer, victim = await get_user(message.from_user.id), await get_user(message.reply_to_message.from_user.id)
    if killer['status'] == "dead": return await message.reply_text("You are dead!")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ Protected!")
    await update_user(victim['_id'], {"status": "dead"})
    await update_user(killer['_id'], {"kills": killer['kills'] + 1})
    await message.reply_text("🔪 Killed successfully!")

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
    tax = int(amt * 0.10)
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

@app.on_message(filters.command("pay"))
async def pay(client, message: Message):
    await message.reply_text("💓 **Baka Premium**\nSend ID to @WTF_Phantom.\n\nID: `/id`")

# ---------------- 3. FUN & GROUP LOGIC ---------------- #

@app.on_message(filters.command(["stupid_meter", "brain", "look", "crush", "love"]))
async def meters(client, message: Message):
    # EXACT LOGIC: Group only check
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("🚫 You can use this command in groups only !")
        
    p = random.randint(0, 100)
    cmd = message.command[0]
    await message.reply_text(f"📊 **{cmd.title()} Level:** {p}%")

@app.on_message(filters.command(["slap", "punch", "bite", "kiss", "hug"]))
async def actions(client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to someone!")
    act = message.command[0]
    emojis = {"slap": "👋", "punch": "👊", "bite": "🦷", "kiss": "💋", "hug": "🤗"}
    await message.reply_text(f"{message.from_user.mention} **{act}ed** {message.reply_to_message.from_user.mention} {emojis.get(act, '')}!")

@app.on_message(filters.command(["truth", "dare", "puzzle"]))
async def t_d_p(client, message: Message):
    cmd = message.command[0]
    if cmd == "truth": t = random.choice(["Deepest fear?", "Crush name?"])
    elif cmd == "dare": t = random.choice(["Send a selfie.", "Bark like a dog."])
    else: t = "What is 2+2?"
    await message.reply_text(f"🎲 **{cmd.title()}:** {t}")

@app.on_message(filters.command("tr"))
async def translate(client, message: Message):
    if not message.reply_to_message: return
    res = await asyncio.to_thread(ai_github, f"Translate to English: {message.reply_to_message.text}")
    await message.reply_text(f"🔤 **Translation:**\n{res}")

@app.on_message(filters.command("id"))
async def id_cmd(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    await message.reply_text(f"🆔 **ID:** `{target.id}`")

@app.on_message(filters.command("adminlist"))
async def adminlist(client, message: Message):
    if message.chat.type == ChatType.PRIVATE: return
    admins = [m.user.mention async for m in client.get_chat_members(message.chat.id, filter=ChatMemberStatus.ADMINISTRATOR)]
    await message.reply_text("👮‍♂️ **Admins:**\n" + "\n".join(admins))

# ---------------- 4. AI ENGINE ---------------- #

def ai_github(text):
    if not GITHUB_TOKEN: return None
    try:
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GITHUB_TOKEN}"}
        payload = {"messages": [{"role": "system", "content": "You are Baka, a sassy female bot. Reply in Hinglish."}, {"role": "user", "content": text}], "model": "gpt-4o", "temperature": 0.8}
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200: return res.json()["choices"][0]["message"]["content"]
    except: pass
    return None

def ai_pollinations(text):
    try:
        url = f"https://text.pollinations.ai/{urllib.parse.quote(text)}?seed={random.randint(1,999)}&model=openai&system=You are Baka, sassy bot."
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
        await message.reply_text(res if res else "Server busy 😵‍💫")

# ---------------- 5. STARTUP ---------------- #

async def main():
    print("Bot Starting...")
    await app.start()
    
    # FULL COMMAND LIST
    commands = [
        ("start", "Talk to Baka"), ("pay", "Buy premium access"), ("check", "Check protection"),
        ("daily", "Claim $1000 daily reward"), ("claim", "Add baka in groups and claim"),
        ("own", "Make your own sticker pack"), ("help", "Show admin commands"),
        ("open", "Open gaming commands"), ("close", "Close gaming commands"),
        ("music", "get the random music list"), ("couples", "Choose random couples"),
        ("crush", "Reply to someone"), ("love", "Reply to someone"), ("look", "Reply to someone"),
        ("brain", "Reply to someone"), ("stupid_meter", "Reply to someone"),
        ("slap", "Reply to someone"), ("punch", "Reply to someone"), ("bite", "Reply to someone"),
        ("kiss", "Reply to someone"), ("hug", "Reply to someone"), ("truth", "Picks a truth"),
        ("dare", "Picks a dare"), ("puzzle", "Picks a puzzle"), ("tr", "Translate any text"),
        ("detail", "Know about past names/usernames"), ("id", "Reply to someone"),
        ("adminlist", "Check adminlist"), ("owner", "Tag group owner"),
        ("bal", "see ur/ur friend's balance"), ("rob", "Reply to someone"),
        ("kill", "Reply to someone"), ("revive", "Use with or without reply"),
        ("protect", "Protect urself from robbery"), ("give", "Give money to the replied user"),
        ("toprich", "See top 10 users globally"), ("topkill", "See top 10 killers globally"),
        ("item", "Use with or without reply"), ("items", "Check all available items"),
        ("gift", "Gift a item"), ("economy", "See all economy commands")
    ]
    await app.set_bot_commands([BotCommand(c, d) for c, d in commands])
    print("Bot is Alive!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
