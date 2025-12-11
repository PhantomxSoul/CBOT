import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# ---------------- CONFIGURATION (ENV VARS) ---------------- #
# Heroku ke "Settings" -> "Config Vars" se ye values uthayega
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME") # e.g. BakaBot (without @)

app = Client("baka_clone", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- MOCK DATABASE ---------------- #
# Note: Heroku dyno restart hone par ye data udd jayega.
# Permanent storage ke liye MongoDB use karna padega.
user_db = {}

def get_user_data(user_id, name):
    if user_id not in user_db:
        return None
    return user_db[user_id]

def register_user(user_id):
    if user_id in user_db:
        return False
    user_db[user_id] = {
        "balance": 5000,
        "status": "alive",
        "kills": 0,
        "protected_until": 0
    }
    return True

# ---------------- COMMANDS ---------------- #

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    chat_type = message.chat.type
    
    txt = (
        f"✨ 𝐇𝐞𝐲 {message.from_user.mention} ~\n"
        f"𖦹 𝒀𝒐𝒖'𝒓𝒆 𝒕𝒂𝒍𝒌𝒊𝒏𝒈 𝒕𝒐 𝑩𝒂𝒌𝒂, 𝒂 𝒔𝒂𝒔𝒔𝒚 𝒄𝒖𝒕𝒊𝒆 𝒃𝒐𝒕 💕\n\n"
        f"𖥔 Choose an option below:"
    )

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("Talk to baka💬", callback_data="talk_info")],
        [InlineKeyboardButton("Friends", callback_data="friends_info"), InlineKeyboardButton("Games", callback_data="games_info")],
        [InlineKeyboardButton("Add me to your group", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
    ])

    if chat_type == "private":
        await message.reply_text(text=txt, reply_markup=buttons)
    else:
        await message.reply_text("Baka is online! Type /help for commands.")

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    data = query.data
    if data == "talk_info":
        await query.answer("Just send a message in the group to talk to me! 💕", show_alert=True)
    elif data == "friends_info":
        await query.answer("Friend system coming soon!", show_alert=True)
    elif data == "games_info":
        await query.answer("Use /game to play lottery!", show_alert=True)

@app.on_message(filters.command("register"))
async def register_cmd(client, message: Message):
    if register_user(message.from_user.id):
        await message.reply_text("🎉 Registration successful! +5000 added 💸")
    else:
        await message.reply_text("✨ You are already registered !!")

@app.on_message(filters.command("bal"))
async def balance_cmd(client, message: Message):
    user_id = message.from_user.id
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    
    data = get_user_data(user_id, "")
    if not data:
        await message.reply_text("User is not registered! Use /register")
        return

    txt = (
        f"👤 Name: {message.from_user.mention}\n"
        f"💰 Total Balance: ${data['balance']}\n"
        f"🏆 Global Rank: 999\n"
        f"❤️ Status: {data['status']}\n"
        f"⚔️ Kills: {data['kills']}"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("revive"))
async def revive_cmd(client, message: Message):
    user_id = message.from_user.id
    data = get_user_data(user_id, "")
    
    if not data: return
    
    if data['balance'] < 500:
        await message.reply_text(f"❌ You need $500, but have only ${data['balance']}")
        return
        
    data['balance'] -= 500
    data['status'] = "alive"
    await message.reply_text("❤️ You revived yourself! -$500")

@app.on_message(filters.command("protect"))
async def protect_cmd(client, message: Message):
    user_id = message.from_user.id
    data = get_user_data(user_id, "")
    
    if not data: return
    if len(message.command) < 2:
        await message.reply_text("⚠️ Usage: /protect 1d or /protect 2d")
        return
        
    duration = message.command[1]
    cost = 2000 if duration == "1d" else 3500
    seconds = 86400 if duration == "1d" else 172800
    
    if data['balance'] < cost:
        await message.reply_text(f"❌ You need ${cost}!")
        return
        
    data['balance'] -= cost
    data['protected_until'] = time.time() + seconds
    await message.reply_text(f"🛡️ Protected for {duration}!")

@app.on_message(filters.command("help"))
async def help_cmd(client, message: Message):
    await message.reply_text("Available commands:\n/register, /bal, /revive, /kill, /protect, /help")

print("Bot is Starting on Heroku...")
app.run()
