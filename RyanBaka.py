import os
import time
import random
import asyncio
from pyrogram import Client, filters, idle
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Message, 
    CallbackQuery, 
    ChatPermissions,
    BotCommand
)

# ---------------- CONFIGURATION ---------------- #
# Get these from Heroku Config Vars
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")

app = Client("baka_clone", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- MOCK DATABASE ---------------- #
user_db = {}

def get_user(user_id, name="User"):
    if user_id not in user_db:
        user_db[user_id] = {
            "name": name,
            "balance": 0,
            "status": "alive",
            "kills": 0,
            "premium": False,
            "last_daily": 0,
            "protected_until": 0,
            "warns": 0
        }
    return user_db[user_id]

# ---------------- 1. START MENU (FIXED) ---------------- #

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    # Register user in background
    get_user(message.from_user.id, message.from_user.first_name)
    
    # Exact Text from Screenshot
    txt = (
        f"✨ 𝐇𝐞𝐲 {message.from_user.mention} ~\n"
        f"𖦹 𝒀𝒐𝒖'𝒓𝒆 𝒕𝒂𝒍𝒌𝒊𝒏𝒈 𝒕𝒐 𝑩𝒂𝒌𝒂, 𝒂 𝒔𝒂𝒔𝒔𝒚 𝒄𝒖𝒕𝒊𝒆 𝒃𝒐𝒕 💕\n\n"
        f"𖥔 Choose an option below:"
    )

    # Exact Buttons from Screenshot
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✨ 𝐓𝐚𝐥𝐤 𝐭𝐨 𝑩𝒂𝒌𝒂 💬", callback_data="talk_info")
        ],
        [
            InlineKeyboardButton("✨ 𝑭𝒓𝒊𝒆𝒏𝒅𝒔 🧸", callback_data="friends_info"),
            InlineKeyboardButton("✨ 𝑮𝒂𝒎𝒆𝒔 🎮", callback_data="games_info")
        ],
        [
            InlineKeyboardButton("➕ Add me to your group 👥", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")
        ]
    ])

    # Show Menu in BOTH Private and Groups
    await message.reply_text(text=txt, reply_markup=buttons)

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    if query.data == "talk_info":
        await query.answer("Just send a message in the group! 💕", show_alert=True)
    elif query.data == "friends_info":
        await query.answer("Friend system coming soon! 🧸", show_alert=True)
    elif query.data == "games_info":
        await query.answer("Use /economy to see games! 🎮", show_alert=True)

# ---------------- 2. HELP & ECONOMY GUIDES ---------------- #

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    # Exact Text from Screenshot 2
    txt = (
        "🛡️ **Admin Commands (.prefix only):**\n"
        ".warn [reply] - Warn a user (3 = ban)\n"
        ".unwarn [reply] - Remove 1 warning\n"
        ".mute [reply] - Mute temporarily/permanently\n"
        ".unmute [reply] - Unmute the user\n"
        ".ban [reply] - Ban user\n"
        ".unban [reply] - Unban user\n"
        ".kick [reply] - Kick from group\n"
        ".promote [reply] 1/2/3 - Promote replied user to admin\n"
        ".demote [reply] - Demote admin\n"
        ".title [tag] [reply] - Set custom title\n"
        ".pin [reply] - Pin a message\n"
        ".unpin - Unpin the current message\n"
        ".del - delete a message\n"
        ".help - Show this help\n\n"
        "To talk to me, just send me any message 💬✨\n\n"
        "🎮 **Game Features**\n"
        "To know about the Lottery System, tap /game\n"
        "To know about the Economy System, tap /economy\n\n"
        "Have fun and be lucky 🍀"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("economy"))
async def economy_command(client, message: Message):
    # Exact Text from Screenshot 1 & 3
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
        "• /protect 1d|2d|3d — Buy protection (avoid robbery)\n"
    )
    await message.reply_text(txt)

# ---------------- 3. ECONOMY COMMANDS ---------------- #

@app.on_message(filters.command("bal"))
async def balance_cmd(client, message: Message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    name = message.reply_to_message.from_user.first_name if message.reply_to_message else message.from_user.first_name
    
    data = get_user(user_id, name)
    icon = "💖" if data['premium'] else "👤"
    
    txt = (
        f"{icon} Name: {data['name']}\n"
        f"💰 Total Balance: ${data['balance']}\n"
        f"🏆 Global Rank: {random.randint(100, 1000)}\n"
        f"❤️ Status: {data['status']}\n"
        f"⚔️ Kills: {data['kills']}"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("register"))
async def register_cmd(client, message: Message):
    if message.from_user.id in user_db:
        await message.reply_text("✨ You are already registered !!")
    else:
        get_user(message.from_user.id, message.from_user.first_name)
        user_db[message.from_user.id]['balance'] = 5000
        await message.reply_text("🎉 Registration successful! +5000 added 💸")

@app.on_message(filters.command("daily"))
async def daily_cmd(client, message: Message):
    data = get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    
    if now - data['last_daily'] < 86400:
        hours = int((86400 - (now - data['last_daily'])) / 3600)
        await message.reply_text(f"⏳ Please wait {hours} hours!")
        return
        
    reward = 2000 if data['premium'] else 1000
    data['balance'] += reward
    data['last_daily'] = now
    await message.reply_text(f"💰 Collected ${reward} daily reward!")

@app.on_message(filters.command("pay"))
async def pay_premium(client, message: Message):
    data = get_user(message.from_user.id)
    if data['premium']:
        await message.reply_text("💖 You are already Premium!")
        return
    if data['balance'] < 50000:
        await message.reply_text("❌ You need $50,000 for Premium!")
        return
    data['balance'] -= 50000
    data['premium'] = True
    await message.reply_text("🎉 You are now a Premium User 💖!")

@app.on_message(filters.command("revive"))
async def revive_cmd(client, message: Message):
    data = get_user(message.from_user.id)
    if data['status'] == "alive":
        await message.reply_text("❤️ You are already alive!")
        return
    if data['balance'] < 500:
        await message.reply_text("❌ You need $500 to revive!")
        return
    data['balance'] -= 500
    data['status'] = "alive"
    await message.reply_text("❤️ You revived yourself! -$500")

@app.on_message(filters.command("kill"))
async def kill_cmd(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("Reply to someone! 😈")
        return
    
    killer = get_user(message.from_user.id)
    victim = get_user(message.reply_to_message.from_user.id)
    
    if killer['status'] == "dead":
        await message.reply_text("You are dead! /revive first.")
        return
    if victim['status'] == "dead":
        await message.reply_text("They are already dead.")
        return
    if time.time() < victim['protected_until']:
        await message.reply_text("🛡️ They are protected!")
        return
        
    victim['status'] = "dead"
    killer['kills'] += 1
    reward = random.randint(200, 400) if killer['premium'] else random.randint(100, 200)
    killer['balance'] += reward
    
    await message.reply_text(f"⚠️ You killed {message.reply_to_message.from_user.first_name}!\nEarned: ${reward}\nThey are now dead.")

@app.on_message(filters.command("protect"))
async def protect_cmd(client, message: Message):
    if len(message.command) < 2:
        await message.reply_text("⚠️ Usage: /protect 1d or /protect 2d")
        return
        
    duration = message.command[1]
    days_map = {"1d": 1, "2d": 2, "3d": 3}
    if duration not in days_map:
        return
        
    cost = 2000 * days_map[duration]
    data = get_user(message.from_user.id)
    
    if data['balance'] < cost:
        await message.reply_text(f"❌ You need ${cost}!")
        return
        
    data['balance'] -= cost
    data['protected_until'] = time.time() + (86400 * days_map[duration])
    await message.reply_text(f"🛡️ You are now protected for {duration}.")

@app.on_message(filters.command("give"))
async def give_cmd(client, message: Message):
    if not message.reply_to_message or len(message.command) < 2:
        await message.reply_text("Usage: /give [amount] (replying to user)")
        return
        
    try: amount = int(message.command[1])
    except: return
    
    sender = get_user(message.from_user.id)
    receiver = get_user(message.reply_to_message.from_user.id)
    
    if sender['balance'] < amount:
        await message.reply_text("❌ Low balance.")
        return
        
    tax = int(amount * (0.05 if sender['premium'] else 0.10))
    sender['balance'] -= amount
    receiver['balance'] += (amount - tax)
    await message.reply_text(f"💸 Sent ${amount - tax} (Tax: ${tax})")

@app.on_message(filters.command("toprich"))
async def toprich(client, message: Message):
    top = sorted(user_db.values(), key=lambda x: x['balance'], reverse=True)[:10]
    txt = "🏆 **Top Richest Users**\n\n"
    for i, u in enumerate(top, 1):
        txt += f"{i}. {u['name']} - ${u['balance']}\n"
    await message.reply_text(txt)

# ---------------- 4. ADMIN COMMANDS (DOT PREFIX) ---------------- #

async def check_admin(message):
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ["administrator", "creator"]
    except:
        return False

@app.on_message(filters.command("ban", prefixes=".") & filters.group)
async def ban_user(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    try:
        await client.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        await message.reply_text("🚫 Banned!")
    except: await message.reply_text("I need admin rights.")

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

@app.on_message(filters.command("del", prefixes=".") & filters.group)
async def delete_msg(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    try:
        await message.reply_to_message.delete()
        await message.delete()
    except: pass

# ---------------- 5. STARTUP & MENU SETUP ---------------- #

async def main():
    print("Bot is starting...")
    async with app:
        # This sets the "/" menu commands in Telegram automatically
        await app.set_bot_commands([
            BotCommand("start", "Start Baka Bot"),
            BotCommand("help", "Get Admin Commands"),
            BotCommand("economy", "Economy Guide"),
            BotCommand("bal", "Check Balance"),
            BotCommand("daily", "Claim Daily Reward"),
            BotCommand("kill", "Kill a user"),
            BotCommand("revive", "Revive yourself"),
            BotCommand("protect", "Buy Protection"),
            BotCommand("pay", "Buy Premium"),
            BotCommand("toprich", "Leaderboard"),
        ])
        print("Commands Set! Bot is running...")
        await idle()

if __name__ == "__main__":
    app.run(main())
