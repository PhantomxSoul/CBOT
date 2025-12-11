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
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")
# Add your ID here in Heroku Config Vars to use Admin/Sudo commands
OWNER_ID = int(os.environ.get("OWNER_ID", "0")) 

app = Client("baka_clone", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ---------------- MOCK DATABASE ---------------- #
# Stores: {user_id: {'name': str, 'balance': int, 'premium': bool, ...}}
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
    # Update name if changed
    if name != "User": 
        user_db[user_id]["name"] = name
    return user_db[user_id]

# ---------------- 1. START MENU ---------------- #

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
        [InlineKeyboardButton("✨ 𝑭𝒓𝒊𝒆𝒏𝒅𝒔 🧸", callback_data="friends_info"),
         InlineKeyboardButton("✨ 𝑮𝒂𝒎𝒆𝒔 🎮", callback_data="games_info")],
        [InlineKeyboardButton("➕ Add me to your group 👥", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
    ])
    await message.reply_text(text=txt, reply_markup=buttons)

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    if query.data == "talk_info":
        await query.answer("Just send a message in the group! 💕", show_alert=True)
    elif query.data == "games_info":
        await query.answer("Use /economy to see games! 🎮", show_alert=True)

# ---------------- 2. EXACT REPLIES (REQUESTED) ---------------- #

@app.on_message(filters.command("daily"))
async def daily_cmd(client, message: Message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    
    # Cooldown Check
    if now - user['last_daily'] < 86400:
        hours = int((86400 - (now - user['last_daily'])) / 3600)
        await message.reply_text(f"⏳ Please wait {hours} hours!")
        return

    # Reward Logic
    reward = 2000 if user['premium'] else 1000
    user['balance'] += reward
    user['last_daily'] = now

    # EXACT RESPONSE FORMAT
    if user['premium']:
         await message.reply_text(f"✅ You received: ${reward} daily reward! (Premium 🌟)")
    else:
        await message.reply_text(
            f"✅ You received: ${reward} daily reward!\n"
            f"💓 Upgrade to premium using /pay to get $2000 daily reward!"
        )

@app.on_message(filters.command("pay"))
async def pay_cmd(client, message: Message):
    # EXACT RESPONSE FORMAT
    txt = (
        "💓 **Baka Premium Access Link**\n\n"
        "👇 **Important Note :**\n\n"
        "1. You must enter your Telegram ID (Numeric ID) on the payment page.\n"
        "It's not necessary to provide real phone number on payment page\n\n"
        ".2. Upon successful payment, you will receive automatic premium access.\n\n"
        "3. You can check your Telegram ID using this command : /id \n\n"
        "Thank you! 💓\n\n\n"
        "Here is your payment link: @WTF_Phantom"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("id"))
async def id_cmd(client, message: Message):
    # EXACT RESPONSE FORMAT
    txt = (
        f"👤 **Your User ID:** `{message.from_user.id}`\n"
        f"💬 **Chat ID:** `{message.chat.id}`"
    )
    await message.reply_text(txt)

# ---------------- 3. SUDO / OWNER COMMANDS ---------------- #

@app.on_message(filters.command("makepremium") & filters.user(OWNER_ID))
async def make_premium(client, message: Message):
    try:
        # Check if ID is provided
        if len(message.command) < 2:
            await message.reply_text("⚠️ Usage: `/makepremium 123456789`")
            return

        target_id = int(message.command[1])
        
        # Initialize user if not in DB
        if target_id not in user_db:
            get_user(target_id, "Unknown User")
            
        user_db[target_id]['premium'] = True
        
        await message.reply_text(f"✅ User `{target_id}` is now **Premium**! 💓")
        
        # Optional: Notify the user
        try:
            await client.send_message(target_id, "🎉 You have been upgraded to **Premium** by the Owner! 💓")
        except:
            pass # User might have blocked bot
            
    except ValueError:
        await message.reply_text("❌ Invalid ID format.")

@app.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def remove_premium(client, message: Message):
    try:
        if len(message.command) < 2:
            await message.reply_text("⚠️ Usage: `/removepremium 123456789`")
            return

        target_id = int(message.command[1])
        
        if target_id in user_db:
            user_db[target_id]['premium'] = False
            await message.reply_text(f"💔 User `{target_id}` removed from Premium.")
        else:
            await message.reply_text("❌ User not found in database.")
            
    except ValueError:
        await message.reply_text("❌ Invalid ID format.")

@app.on_message(filters.command("premiumlist") & filters.user(OWNER_ID))
async def premium_list(client, message: Message):
    txt = "📋 **List of Premium Users:**\n\n"
    count = 0
    
    for uid, data in user_db.items():
        if data['premium']:
            count += 1
            # Creates a clickable link to the user
            txt += f"{count}. [{data['name']}](tg://user?id={uid}) (`{uid}`)\n"
            
    if count == 0:
        await message.reply_text("No premium users found.")
    else:
        await message.reply_text(txt)

# ---------------- 4. STANDARD ECONOMY ---------------- #

@app.on_message(filters.command("bal"))
async def bal_cmd(client, message: Message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    data = get_user(user_id, "")
    badge = "💖" if data['premium'] else "👤"
    await message.reply_text(f"{badge} **Balance:** ${data['balance']}\n**Status:** {data['status']}")

@app.on_message(filters.command("kill"))
async def kill_cmd(client, message: Message):
    if not message.reply_to_message: return
    killer = get_user(message.from_user.id)
    victim = get_user(message.reply_to_message.from_user.id)
    
    if killer['status'] == "dead": 
        await message.reply_text("You are dead ☠️")
        return
        
    victim['status'] = "dead"
    killer['kills'] += 1
    reward = random.randint(200, 400) if killer['premium'] else random.randint(100, 200)
    killer['balance'] += reward
    await message.reply_text(f"🔪 Killed! Earned ${reward}")

@app.on_message(filters.command("revive"))
async def revive_cmd(client, message: Message):
    user = get_user(message.from_user.id)
    if user['balance'] >= 500:
        user['balance'] -= 500
        user['status'] = "alive"
        await message.reply_text("❤️ Revived!")
    else:
        await message.reply_text("❌ Need $500")

# ---------------- 5. STARTUP ---------------- #

async def main():
    print("Bot Starting...")
    async with app:
        await app.set_bot_commands([
            BotCommand("start", "Start Bot"),
            BotCommand("daily", "Daily Reward"),
            BotCommand("pay", "Get Premium"),
            BotCommand("id", "Get ID"),
            BotCommand("bal", "Check Balance"),
        ])
        print("Bot is Alive!")
        await idle()

if __name__ == "__main__":
    app.run(main())
