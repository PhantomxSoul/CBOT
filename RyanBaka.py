import os
import time
import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery, ChatPermissions

# ---------------- CONFIGURATION ---------------- #
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")

app = Client("baka_clone", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- MOCK DATABASE ---------------- #
user_db = {}

def get_user(user_id):
    if user_id not in user_db:
        user_db[user_id] = {
            "balance": 0,
            "status": "alive",
            "kills": 0,
            "premium": False,
            "last_daily": 0,
            "protected_until": 0,
            "warns": 0
        }
    return user_db[user_id]

# ---------------- 1. EXACT START MENU REPLICA ---------------- #

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    # 1. The Text (Exact Unicode Fonts from Screenshot)
    txt = (
        f"✨ 𝐇𝐞𝐲 {message.from_user.mention} ~\n"
        f"𖦹 𝒀𝒐𝒖'𝒓𝒆 𝒕𝒂𝒍𝒌𝒊𝒏𝒈 𝒕𝒐 𝑩𝒂𝒌𝒂, 𝒂 𝒔𝒂𝒔𝒔𝒚 𝒄𝒖𝒕𝒊𝒆 𝒃𝒐𝒕 💕\n\n"
        f"𖥔 Choose an option below:"
    )

    # 2. The Buttons (Exact Layout & Fonts)
    buttons = InlineKeyboardMarkup([
        [
            # Row 1: Single Button
            InlineKeyboardButton("✨ 𝐓𝐚𝐥𝐤 𝐭𝐨 𝑩𝒂𝒌𝒂 💬", callback_data="talk_info")
        ],
        [
            # Row 2: Two Buttons (Friends & Games)
            InlineKeyboardButton("✨ 𝑭𝒓𝒊𝒆𝒏𝒅𝒔 🧸", callback_data="friends_info"),
            InlineKeyboardButton("✨ 𝑮𝒂𝒎𝒆𝒔 🎮", callback_data="games_info")
        ],
        [
            # Row 3: Add to Group
            InlineKeyboardButton("➕ Add me to your group 👥", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")
        ]
    ])

    # Send Photo or Text (Text only based on logs, but looks better)
    if message.chat.type == "private":
        await message.reply_text(text=txt, reply_markup=buttons)
    else:
        await message.reply_text("Baka is online! ✨")

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    if query.data == "talk_info":
        await query.answer("Just send a message in the group! 💕", show_alert=True)
    elif query.data == "friends_info":
        await query.answer("Friends system coming soon! 🧸", show_alert=True)
    elif query.data == "games_info":
        await query.answer("Use /economy to see games! 🎮", show_alert=True)

# ---------------- 2. ECONOMY & GAME COMMANDS ---------------- #

@app.on_message(filters.command("economy"))
async def economy_help(client, message: Message):
    txt = (
        "💰 **Baka Economy System Guide**\n\n"
        "🔹 **Normal Users (👤):**\n"
        "• /daily — Receive $1000 daily reward\n"
        "• /bal — Check balance\n"
        "• /rob (reply) — Rob user (Max $10k)\n"
        "• /kill (reply) — Reward $100-200\n"
        "• /revive — Revive yourself ($500)\n"
        "• /protect 1d — Buy protection ($2000)\n"
        "• /give (reply) amount — Gift money (10% fee)\n\n"
        "🔸 **Premium Users (💖):**\n"
        "• /pay — Buy Premium (Cost: $50,000)\n"
        "• /daily — Receive $2000\n"
        "• /rob — Max $100k limit\n"
        "• /kill — Reward $200-400\n"
        "• /protect 1d/2d/3d — Extended protection\n"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("bal"))
async def check_balance(client, message: Message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = get_user(user_id)
    badge = "💖" if user['premium'] else "👤"
    
    txt = (
        f"{badge} **Name:** {message.from_user.mention}\n"
        f"💰 **Total Balance:** ${user['balance']}\n"
        f"❤️ **Status:** {user['status']}\n"
        f"⚔️ **Kills:** {user['kills']}"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("daily"))
async def daily_reward(client, message: Message):
    user = get_user(message.from_user.id)
    now = time.time()
    if now - user['last_daily'] < 86400:
        remaining = int((86400 - (now - user['last_daily'])) / 3600)
        await message.reply_text(f"⏳ Come back in {remaining} hours!")
        return

    amount = 2000 if user['premium'] else 1000
    user['balance'] += amount
    user['last_daily'] = now
    await message.reply_text(f"💰 You claimed ${amount} daily reward!")

@app.on_message(filters.command("pay"))
async def buy_premium(client, message: Message):
    user = get_user(message.from_user.id)
    if user['premium']:
        await message.reply_text("💖 You are already Premium!")
        return
    if user['balance'] < 50000:
        await message.reply_text("❌ You need $50,000 to buy Premium!")
        return
    user['balance'] -= 50000
    user['premium'] = True
    await message.reply_text("🎉 You are now a **Premium User** 💖!")

@app.on_message(filters.command("kill"))
async def kill_user(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("Reply to someone to kill! 🔪")
        return
    
    killer = get_user(message.from_user.id)
    victim = get_user(message.reply_to_message.from_user.id)

    if killer['status'] == "dead":
        await message.reply_text("❌ You are dead! Use /revive")
        return
    if victim['status'] == "dead":
        await message.reply_text("☠️ They are already dead!")
        return
    if time.time() < victim['protected_until']:
        await message.reply_text("🛡️ They are protected!")
        return

    victim['status'] = "dead"
    killer['kills'] += 1
    reward = random.randint(200, 400) if killer['premium'] else random.randint(100, 200)
    killer['balance'] += reward
    await message.reply_text(f"🔪 You killed {message.reply_to_message.from_user.mention} and earned ${reward}!")

@app.on_message(filters.command("revive"))
async def revive_user(client, message: Message):
    user = get_user(message.from_user.id)
    if user['status'] == "alive":
        await message.reply_text("You are already alive! ❤️")
        return
    if user['balance'] < 500:
        await message.reply_text("❌ You need $500 to revive!")
        return
    user['balance'] -= 500
    user['status'] = "alive"
    await message.reply_text("❤️ You revived yourself!")

@app.on_message(filters.command("give"))
async def give_money(client, message: Message):
    if not message.reply_to_message: return
    try: amount = int(message.command[1])
    except: return
    sender = get_user(message.from_user.id)
    receiver = get_user(message.reply_to_message.from_user.id)
    if sender['balance'] < amount:
        await message.reply_text("❌ Insufficient balance!")
        return
    tax = int(amount * (0.05 if sender['premium'] else 0.10))
    sender['balance'] -= amount
    receiver['balance'] += (amount - tax)
    await message.reply_text(f"💸 Sent ${amount-tax} (Tax: ${tax})")

@app.on_message(filters.command("protect"))
async def protect_user(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("Usage: /protect 1d")
        return
    duration_map = {"1d": 86400, "2d": 172800, "3d": 259200}
    choice = message.command[1]
    if choice not in duration_map: return
    user = get_user(message.from_user.id)
    cost = 2000 * int(choice[0])
    if user['balance'] < cost:
        await message.reply_text(f"❌ You need ${cost}!")
        return
    user['balance'] -= cost
    user['protected_until'] = time.time() + duration_map[choice]
    await message.reply_text(f"🛡️ Protected for {choice}!")

@app.on_message(filters.command("toprich"))
async def toprich(client, message: Message):
    sorted_users = sorted(user_db.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    txt = "🏆 **Top Richest Users**\n\n"
    for idx, (uid, data) in enumerate(sorted_users, 1):
        txt += f"{idx}. ID: {uid} — ${data['balance']}\n"
    await message.reply_text(txt)

# ---------------- 3. ADMIN DOT COMMANDS ---------------- #

async def check_admin(message):
    member = await message.chat.get_member(message.from_user.id)
    return member.status in ["administrator", "creator"]

@app.on_message(filters.command("ban", prefixes=".") & filters.group)
async def ban_member(client, message: Message):
    if not await check_admin(message): return
    if not message.reply_to_message: return
    try:
        await client.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        await message.reply_text(f"🚫 Banned {message.reply_to_message.from_user.mention}")
    except: pass

@app.on_message(filters.command("mute", prefixes=".") & filters.group)
async def mute_member(client, message: Message):
    if not await check_admin(message): return
    if not message.reply_to_message: return
    try:
        await client.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=False))
        await message.reply_text(f"🤐 Muted {message.reply_to_message.from_user.mention}")
    except: pass

@app.on_message(filters.command("unmute", prefixes=".") & filters.group)
async def unmute_member(client, message: Message):
    if not await check_admin(message): return
    if not message.reply_to_message: return
    try:
        await client.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=True))
        await message.reply_text(f"🗣️ Unmuted {message.reply_to_message.from_user.mention}")
    except: pass

@app.on_message(filters.command("warn", prefixes=".") & filters.group)
async def warn_user(client, message: Message):
    if not await check_admin(message): return
    if not message.reply_to_message: return
    victim_id = message.reply_to_message.from_user.id
    user = get_user(victim_id)
    user['warns'] += 1
    await message.reply_text(f"⚠️ Warned! {user['warns']}/3")
    if user['warns'] >= 3:
        try:
            await client.ban_chat_member(message.chat.id, victim_id)
            await message.reply_text("🚫 User banned (3/3 warnings).")
            user['warns'] = 0
        except: pass

@app.on_message(filters.command("pin", prefixes=".") & filters.group)
async def pin_msg(client, message: Message):
    if not await check_admin(message): return
    if message.reply_to_message: await message.reply_to_message.pin()

@app.on_message(filters.command("del", prefixes=".") & filters.group)
async def del_msg(client, message: Message):
    if not await check_admin(message): return
    if message.reply_to_message:
        await message.reply_to_message.delete()
        await message.delete()

print("Baka v3 (Final UI Fix) is Starting...")
app.run()
