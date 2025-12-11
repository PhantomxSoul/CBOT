import os
import time
import asyncio
import google.generativeai as genai
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatType, ChatAction
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ---------------- AI SETUP (MULTI-MODEL BACKUP) ---------------- #
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # SAFETY: Disable filters so Baka can be sassy
    SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    # PRIORITY LIST: Try these models in order
    # We use the models available in your provided list
    MODEL_LIST = [
        "models/gemini-2.5-flash",       # 1. Best & Newest
        "models/gemini-2.0-flash",       # 2. Stable Backup
        "models/gemini-2.0-flash-lite",  # 3. Lightweight Backup
        "models/gemini-2.5-flash-lite"   # 4. Final Backup
    ]
else:
    MODEL_LIST = []
    print("⚠️ GEMINI_API_KEY MISSING")

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

# ---------------- 3. ADMIN & PAYMENT ---------------- #

@app.on_message(filters.command("pay"))
async def pay_cmd(client, message: Message):
    txt = (
        "💓 **Baka Premium Access Link**\n\n"
        "👇 **Important Note:**\n"
        "Send your ID to @WTF_Phantom after payment.\n\n"
        f"Your ID: `/id`"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("id"))
async def id_cmd(client, message: Message):
    await message.reply_text(f"👤 Your ID: `{message.from_user.id}`")

# ---------------- 4. SMART AI ENGINE (AUTO-FALLBACK) ---------------- #

def get_ai_response(user_text):
    if not GEMINI_API_KEY:
        return "⚠️ Error: GEMINI_API_KEY Missing!"
    
    persona = "You are Baka, a sassy female Telegram bot. Reply in Hinglish (Hindi + English). Be savage, cute, and use emojis. Keep replies short."
    full_prompt = f"{persona}\nUser: {user_text}"
    
    # Try models one by one
    for model_name in MODEL_LIST:
        try:
            # Configure Model
            model = genai.GenerativeModel(model_name, safety_settings=SAFETY_SETTINGS)
            
            # Generate Response
            response = model.generate_content(full_prompt)
            
            # If successful, return text
            if response.text:
                return response.text
                
        except Exception as e:
            # If 404 (Not Found) or other error, print and try next model
            print(f"FAILED {model_name}: {e}")
            continue # Try next model in list
            
    return "Oof, Google servers died! 😵‍💫 (All models failed)"

@app.on_message(filters.text)
async def chat_handler(client, message: Message):
    # Skip Commands
    if message.text.startswith("/") or message.text.startswith("."):
        return

    # Logic
    is_private = message.chat.type == ChatType.PRIVATE
    is_mentioned = message.mentioned
    is_reply = False
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.is_self:
            is_reply = True

    if is_private or is_mentioned or is_reply:
        try:
            await client.send_chat_action(message.chat.id, ChatAction.TYPING)
            reply = await asyncio.to_thread(get_ai_response, message.text)
            await message.reply_text(reply)
        except Exception as e:
            print(f"HANDLER CRASH: {e}")

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
