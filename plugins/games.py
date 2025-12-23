import time
import random
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.types import Message
# IMPORT CONFIG
from config import MONGO_URL
# IMPORT HELPER TEXTS
from plugins.helper import ECONOMY_TEXT, GAME_OPEN_TEXT, GAME_CLOSE_TEXT

# --- DATABASE CONNECTION ---
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot
users_col = db.users
chats_col = db.chats

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

# --- HELPER FUNCTIONS ---
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
            "items": {} 
        }
        await users_col.insert_one(user)
    return user

async def update_user(user_id, data):
    await users_col.update_one({"_id": user_id}, {"$set": data})

async def is_admin(message: Message):
    if message.chat.type == ChatType.PRIVATE: return False
    try:
        mem = await message.chat.get_member(message.from_user.id)
        return mem.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except: return False

async def is_game_enabled(chat_id):
    chat = await chats_col.find_one({"_id": chat_id})
    return chat.get("games_enabled", True) if chat else True

# ---------------- MANAGEMENT COMMANDS ---------------- #

@Client.on_message(filters.command("check"))
async def check_premium_cmd(client: Client, message: Message):
    user = await get_user(message.from_user.id, message.from_user.first_name)
    
    # PREMIUM CHECK LOGIC
    if not user.get("premium", False):
        # CORRECTED: Only sends the Bot's reply part
        return await message.reply_text(
            "𝐁ᴀᴋᴀ 💗:\n"
            "❌ This command is only for Premium users."
        )
        
    # IF PREMIUM
    rem = user.get('protected_until', 0) - time.time()
    prot_status = f"Active ({int(rem/3600)}h left) 🛡️" if rem > 0 else "Inactive ❌"
    
    await message.reply_text(
        f"💎 **Premium Dashboard**\n"
        f"👤 {message.from_user.mention}\n"
        f"🛡️ **Protection:** {prot_status}\n"
        f"✅ **Daily Limit:** $2000"
    )

@Client.on_message(filters.command("open") & filters.group)
async def open_games(client: Client, message: Message):
    if not await is_admin(message):
        return await message.reply_text("❌ You need to be an Admin to use this!")
    
    await chats_col.update_one({"_id": message.chat.id}, {"$set": {"games_enabled": True}}, upsert=True)
    await message.reply_text(GAME_OPEN_TEXT)

@Client.on_message(filters.command("close") & filters.group)
async def close_games(client: Client, message: Message):
    if not await is_admin(message):
        return await message.reply_text("❌ You need to be an Admin to use this!")
    
    await chats_col.update_one({"_id": message.chat.id}, {"$set": {"games_enabled": False}}, upsert=True)
    await message.reply_text(GAME_CLOSE_TEXT)

@Client.on_message(filters.command("claim") & filters.group)
async def claim_reward(client: Client, message: Message):
    # Only Admins can claim
    if not await is_admin(message):
        return await message.reply_text("❌ Only Admins can claim the group reward!")

    chat_id = message.chat.id
    user_id = message.from_user.id
    
    chat_data = await chats_col.find_one({"_id": chat_id})
    if chat_data and chat_data.get("claimed", False):
        return await message.reply_text("❌ This group has already claimed the start reward!")
        
    # Give Reward
    reward = 5000
    await update_user(user_id, {"balance": (await get_user(user_id))['balance'] + reward})
    await chats_col.update_one({"_id": chat_id}, {"$set": {"claimed": True}}, upsert=True)
    
    await message.reply_text(f"✅ **Group Reward Claimed!**\n👤 {message.from_user.mention} got ${reward}!")

# ---------------- ECONOMY COMMANDS ---------------- #

@Client.on_message(filters.command("economy"))
async def economy_cmd(client: Client, message: Message):
    await message.reply_text(ECONOMY_TEXT)

@Client.on_message(filters.command("daily"))
async def daily(client: Client, message: Message):
    if not await is_game_enabled(message.chat.id): return
    user = await get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    if now - user['last_daily'] < 86400: return await message.reply_text("⏳ Please wait 24 hours!")
    reward = 2000 if user['premium'] else 1000
    await update_user(user['_id'], {"balance": user['balance'] + reward, "last_daily": now})
    await message.reply_text(f"✅ Received ${reward}!")

@Client.on_message(filters.command("bal"))
async def bal(client: Client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    data = await get_user(target.id, target.first_name)
    badge = "💎" if data['premium'] else "👤"
    await message.reply_text(f"{badge} **Name:** {data['name']}\n💰 **Balance:** ${data['balance']}\n❤️ **Status:** {data['status']}")

@Client.on_message(filters.command("rob"))
async def rob(client: Client, message: Message):
    if not await is_game_enabled(message.chat.id): return
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

@Client.on_message(filters.command("kill"))
async def kill(client: Client, message: Message):
    if not await is_game_enabled(message.chat.id): return
    if not message.reply_to_message: return
    
    killer = await get_user(message.from_user.id)
    victim = await get_user(message.reply_to_message.from_user.id)
    
    if killer['status'] == "dead": return await message.reply_text("You are dead!")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ Protected!")
    
    await update_user(victim['_id'], {"status": "dead"})
    await update_user(killer['_id'], {"kills": killer['kills'] + 1})
    await message.reply_text("🔪 Killed successfully!")

@Client.on_message(filters.command("revive"))
async def revive(client: Client, message: Message):
    if not await is_game_enabled(message.chat.id): return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    t_data = await get_user(target.id)
    p_data = await get_user(message.from_user.id)

    if t_data['status'] == "alive":
        return await message.reply_text(f"✅ {target.mention} is already alive!")
    if p_data['balance'] < 500:
        return await message.reply_text(f"❌ You need $500 to revive!")

    await update_user(p_data['_id'], {"balance": p_data['balance'] - 500})
    await update_user(t_data['_id'], {"status": "alive"})
    await message.reply_text(f"❤️ Revived {target.mention}!")

@Client.on_message(filters.command("protect"))
async def protect(client: Client, message: Message):
    if len(message.command) < 2: return await message.reply_text("Usage: /protect 1d (Cost: $2000/day)")
    
    days_map = {"1d": 1, "2d": 2, "3d": 3}
    days = days_map.get(message.command[1])
    if not days: return await message.reply_text("Invalid duration. Use 1d, 2d, or 3d.")
    
    user = await get_user(message.from_user.id)
    
    # PREMIUM CHECK for > 1 day
    if days > 1 and not user.get('premium', False):
        return await message.reply_text("❌ 2d and 3d protection is for Premium Users only!")
        
    cost = 2000 * days
    if user['balance'] < cost: return await message.reply_text(f"❌ Low Balance. You need ${cost}")
    
    new_expiry = time.time() + (86400 * days)
    await update_user(user['_id'], {"balance": user['balance'] - cost, "protected_until": new_expiry})
    await message.reply_text(f"🛡️ **Protection Activated!**\nDuration: {message.command[1]}")

@Client.on_message(filters.command("give"))
async def give(client: Client, message: Message):
    if not message.reply_to_message: return
    try: amt = int(message.command[1])
    except: return await message.reply_text("Usage: /give [amount]")
    
    sender = await get_user(message.from_user.id)
    if sender['balance'] < amt: return await message.reply_text("❌ Low balance.")
    
    rec = await get_user(message.reply_to_message.from_user.id)
    tax = int(amt * 0.10) # 10% Tax
    
    await update_user(sender['_id'], {"balance": sender['balance'] - amt})
    await update_user(rec['_id'], {"balance": rec['balance'] + (amt - tax)})
    await message.reply_text(f"💸 Sent ${amt-tax} (Tax: ${tax})")

@Client.on_message(filters.command("pay"))
async def pay(client: Client, message: Message):
    await message.reply_text("💓 **Baka Premium**\nSend your ID to @WTF_Phantom to buy.\n\nYour ID: `/id`")

@Client.on_message(filters.command("toprich"))
async def toprich(client: Client, message: Message):
    top = users_col.find().sort("balance", -1).limit(10)
    txt = "🏆 **Top Richest**\n\n"
    i = 1
    async for u in top:
        txt += f"{i}. {u['name']} - ${u['balance']}\n"
        i += 1
    await message.reply_text(txt)

@Client.on_message(filters.command("topkill"))
async def topkill(client: Client, message: Message):
    top = users_col.find().sort("kills", -1).limit(10)
    txt = "⚔️ **Top Killers**\n\n"
    i = 1
    async for u in top:
        txt += f"{i}. {u['name']} - {u['kills']} Kills\n"
        i += 1
    await message.reply_text(txt)

# ---------------- ITEM SHOP & FUN ---------------- #

@Client.on_message(filters.command("items"))
async def shop_list(client: Client, message: Message):
    txt = "📦 **Available Gift Items:**\n\n"
    for key, item in SHOP_ITEMS.items():
        txt += f"{item['emoji']} **{item['name']}** — ${item['cost']}\n"
    await message.reply_text(txt)

@Client.on_message(filters.command("item"))
async def my_items(client: Client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    user = await get_user(target.id, target.first_name)

    items = user.get("items", {})
    if not items:
        return await message.reply_text(f"{target.mention} has no items yet 😢")

    txt = f"🎒 **{target.first_name}'s Items:**\n\n"
    for key, count in items.items():
        if count > 0:
            meta = SHOP_ITEMS.get(key, {"name": key, "emoji": "❓"})
            txt += f"{meta['emoji']} **{meta['name']}**: {count}\n"
    await message.reply_text(txt)

@Client.on_message(filters.command("gift"))
async def gift_item(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to the user you want to gift!")
    try: item_name = message.command[1].lower()
    except: return await message.reply_text("Usage: /gift rose (Reply to user)")

    item_key = None
    for k in SHOP_ITEMS:
        if k in item_name: item_key = k; break
    if not item_key: return await message.reply_text("❌ Item not found! Check /items")

    sender = await get_user(message.from_user.id)
    receiver = await get_user(message.reply_to_message.from_user.id)
    cost = SHOP_ITEMS[item_key]["cost"]

    if sender['balance'] < cost: return await message.reply_text(f"❌ You need ${cost}!")

    r_items = receiver.get("items", {})
    r_items[item_key] = r_items.get(item_key, 0) + 1

    await update_user(sender['_id'], {"balance": sender['balance'] - cost})
    await update_user(receiver['_id'], {"items": r_items})

    await message.reply_text(f"🎁 You gifted {SHOP_ITEMS[item_key]['emoji']} to {message.reply_to_message.from_user.mention}!")

@Client.on_message(filters.command(["stupid_meter", "brain", "look", "crush", "love"]))
async def fun_meters(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE:
        return await message.reply_text("🚫 You can use this command in groups only!")
    p = random.randint(0, 100)
    cmd = message.command[0]
    await message.reply_text(f"📊 **{cmd.title()} Level:** {p}%")

@Client.on_message(filters.command(["slap", "punch", "bite", "kiss", "hug"]))
async def actions(client: Client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to someone!")
    act = message.command[0]
    emojis = {"slap": "👋", "punch": "👊", "bite": "🦷", "kiss": "💋", "hug": "🤗"}
    await message.reply_text(f"{message.from_user.mention} **{act}ed** {message.reply_to_message.from_user.mention} {emojis.get(act, '')}!")

@Client.on_message(filters.command(["truth", "dare", "puzzle"]))
async def t_d_p(client: Client, message: Message):
    cmd = message.command[0]
    if cmd == "truth": t = random.choice(["Deepest fear?", "Crush name?"])
    elif cmd == "dare": t = random.choice(["Send a selfie.", "Bark like a dog."])
    else: t = "What is 2+2?"
    await message.reply_text(f"🎲 **{cmd.title()}:** {t}")

@Client.on_message(filters.command("couples"))
async def couples(client: Client, message: Message):
    if message.chat.type == ChatType.PRIVATE: return await message.reply_text("Groups only!")
    await message.reply_text(f"💘 **Couple of the day:** {message.from_user.mention} ❤️ Baka")

@Client.on_message(filters.command("music"))
async def music_list(client: Client, message: Message):
    await message.reply_text("🎶 **Music List:**\n1. Starboy\n2. Mockingbird\n3. Bones")
