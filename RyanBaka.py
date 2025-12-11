import os
import time
import random
import asyncio
import requests
import urllib.parse
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
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")
OWNER_ID = int(os.environ.get("OWNER_ID", "0")) 

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
            "warns": 0,
            "claimed_group": False
        }
    if name != "User": 
        user_db[user_id]["name"] = name
    return user_db[user_id]

# ---------------- 1. START & MENUS ---------------- #

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    get_user(message.from_user.id, message.from_user.first_name)
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
        "🔹 **Normal Users (👤):**\n"
        "/daily, /bal, /rob, /kill, /revive, /protect, /give\n\n"
        "🔹 **Premium Users (💖):**\n"
        "/pay, /daily ($2000), /rob ($100k limit)"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    txt = "Available Commands:\n/start, /help, /economy, /daily, /bal, /pay, /rob, /kill, /revive, /protect"
    await message.reply_text(txt)

# ---------------- 2. ECONOMY COMMANDS ---------------- #

@app.on_message(filters.command("daily"))
async def daily_cmd(client, message: Message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    if now - user['last_daily'] < 86400:
        return await message.reply_text("⏳ Please wait 24 hours!")
    reward = 2000 if user['premium'] else 1000
    user['balance'] += reward
    user['last_daily'] = now
    await message.reply_text(f"✅ Received ${reward}!")

@app.on_message(filters.command("bal"))
async def bal_cmd(client, message: Message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    data = get_user(user_id, message.from_user.first_name)
    await message.reply_text(f"💰 Balance: ${data['balance']}")

@app.on_message(filters.command("pay"))
async def pay_cmd(client, message: Message):
    txt = (
        "💓 **Baka Premium Access Link**\n\n"
        "👇 **Important Note:**\n"
        "Send your ID to @WTF_Phantom after payment.\n\n"
        "Your ID: `/id`"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("id"))
async def id_cmd(client, message: Message):
    await message.reply_text(f"👤 Your ID: `{message.from_user.id}`")

# ---------------- 3. ADMIN COMMANDS ---------------- #

@app.on_message(filters.command("makepremium") & filters.user(OWNER_ID))
async def make_premium(client, message: Message):
    try:
        target = int(message.command[1])
        get_user(target)
        user_db[target]['premium'] = True
        await message.reply_text(f"✅ User {target} is now Premium!")
    except: pass

# ---------------- 4. AI CHATBOT (DEBUG MODE) ---------------- #

def get_ai_response(user_text):
    try:
        print(f"DEBUG: Generating AI response for: {user_text}") # LOG CHECK
        
        system = "You are Baka, a sassy female Telegram bot. Reply in Hinglish (Hindi+English). Be savage but cute. User says: "
        
        # URL Encode the text
        full_prompt = f"{system} {user_text}"
        encoded_prompt = urllib.parse.quote(full_prompt)
        
        # Pollinations API
        url = f"https://text.pollinations.ai/{encoded_prompt}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print("DEBUG: AI Response received successfully") # LOG CHECK
            return response.text
        else:
            print(f"DEBUG: API Error {response.status_code}") # LOG CHECK
            return "Server busy hai... 😵‍💫"
    except Exception as e:
        print(f"DEBUG: AI Function Error: {e}") # LOG CHECK
        return "Error 😵‍💫"

@app.on_message(filters.text)
async def chat_handler(client, message: Message):
    # 1. Ignore commands
    if message.text.startswith("/") or message.text.startswith("."):
        return

    # 2. DEBUG PRINT - IF YOU DON'T SEE THIS IN LOGS, PRIVACY MODE IS ON
    print(f"DEBUG: Message received from {message.from_user.first_name}: {message.text}")

    # 3. Logic to reply
    is_private = message.chat.type == "private"
    is_mentioned = message.mentioned
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == client.me.id
    
    if is_private or is_mentioned or is_reply_to_bot:
        try:
            await client.send_chat_action(message.chat.id, "typing")
            reply = await asyncio.to_thread(get_ai_response, message.text)
            await message.reply_text(reply)
        except Exception as e:
            print(f"DEBUG: Handler Error: {e}")

# ---------------- 5. STARTUP ---------------- #

async def main():
    print("Bot Starting...")
    async with app:
        await app.set_bot_commands([
            BotCommand("start", "Start Bot"),
            BotCommand("help", "Help Menu"),
            BotCommand("economy", "Economy Guide"),
            BotCommand("daily", "Daily Reward"),
            BotCommand("bal", "Check Balance"),
            BotCommand("pay", "Buy Premium"),
        ])
        print("Bot is Alive!")
        await idle()

if __name__ == "__main__":
    app.run(main())
