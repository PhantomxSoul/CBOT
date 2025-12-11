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
        # 1. Stop the loading animation
        await query.answer()
        # 2. Send the message to the chat (Not as a popup)
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
        ".warn, .mute, .ban, .pin, .del\n\n"
        "To talk to me, just send me any message 💬✨\n\n"
        "🎮 **Game Features**\n"
        "To know about the Lottery System, tap /game\n"
        "To know about the Economy System, tap /economy\n\n"
        "Have fun and be lucky 🍀"
    )
    await message.reply_text(txt)

# ---------------- 2. ECONOMY COMMANDS ---------------- #

@app.on_message(filters.command("claim") & filters.group)
async def claim_cmd(client, message: Message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    if user['claimed_group']:
        await message.reply_text("✨ You have already claimed the group bonus!")
        return
    user['balance'] += 10000
    user['claimed_group'] = True
    await message.reply_text(f"🎉 **Bonus Claimed!**\nYou added Baka to the group and received **$10,000**! 💸")

@app.on_message(filters.command("bal"))
async def bal_cmd(client, message: Message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    name = message.reply_to_message.from_user.first_name if message.reply_to_message else message.from_user.first_name
    data = get_user(user_id, name)
    rank = random.randint(1, 1000)
    txt = (
        f"👤 Name: {data['name']}\n"
        f"💰 Total Balance: ${data['balance']}\n"
        f"🏆 Global Rank: {rank}\n"
        f"❤️ Status: {data['status']}\n"
        f"⚔️ Kills: {data['kills']}"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("daily"))
async def daily_cmd(client, message: Message):
    user = get_user(message.from_user.id, message.from_user.first_name)
    now = time.time()
    if now - user['last_daily'] < 86400:
        hours = int((86400 - (now - user['last_daily'])) / 3600)
        await message.reply_text(f"⏳ Please wait {hours} hours!")
        return
    reward = 2000 if user['premium'] else 1000
    user['balance'] += reward
    user['last_daily'] = now
    if user['premium']:
         await message.reply_text(f"✅ You received: ${reward} daily reward! (Premium 🌟)")
    else:
        await message.reply_text(f"✅ You received: ${reward} daily reward!\n💓 Upgrade to premium using /pay to get $2000 daily reward!")

@app.on_message(filters.command("rob"))
async def rob_cmd(client, message: Message):
    if not message.reply_to_message:
        await message.reply_text("Reply to a user to rob them!")
        return
    try: amount_to_rob = int(message.command[1])
    except: amount_to_rob = 0 
    robber = get_user(message.from_user.id)
    victim = get_user(message.reply_to_message.from_user.id)
    if robber['status'] == "dead": return await message.reply_text("You are dead! ☠️")
    if victim['status'] == "dead": return await message.reply_text("They are already dead ☠️")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ This user is protected!")
    max_limit = 100000 if robber['premium'] else 10000
    if amount_to_rob <= 0 or amount_to_rob > max_limit: amount_to_rob = random.randint(100, max_limit)
    if victim['balance'] < amount_to_rob: amount_to_rob = victim['balance']
    if amount_to_rob <= 0: return await message.reply_text("They have no money! 🥺")
    if random.choice([True, False]):
        victim['balance'] -= amount_to_rob
        robber['balance'] += amount_to_rob
        await message.reply_text(f"💸 **Success!** You stole **${amount_to_rob}** from {message.reply_to_message.from_user.first_name}!")
    else:
        fine = 500
        robber['balance'] -= fine
        await message.reply_text(f"🚔 **Caught!** Police fined you **${fine}**.")

@app.on_message(filters.command("kill"))
async def kill_cmd(client, message: Message):
    if not message.reply_to_message: return await message.reply_text("Reply to someone! 😈")
    killer = get_user(message.from_user.id)
    victim = get_user(message.reply_to_message.from_user.id)
    if killer['status'] == "dead": return await message.reply_text("You are dead! /revive first.")
    if victim['status'] == "dead": return await message.reply_text("They are already dead.")
    if time.time() < victim['protected_until']: return await message.reply_text("🛡️ They are protected!")
    victim['status'] = "dead"
    killer['kills'] += 1
    reward = random.randint(200, 400) if killer['premium'] else random.randint(100, 200)
    killer['balance'] += reward
    await message.reply_text(f"⚠️ You killed {message.reply_to_message.from_user.first_name}!\nEarned: ${reward}\nThey are now dead.")

@app.on_message(filters.command("revive"))
async def revive_cmd(client, message: Message):
    target_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    payer = get_user(message.from_user.id)
    user = get_user(target_id)
    if user['status'] == "alive": return await message.reply_text("Already alive! ❤️")
    if payer['balance'] < 500: return await message.reply_text("❌ You need $500!")
    payer['balance'] -= 500
    user['status'] = "alive"
    await message.reply_text("❤️ Revived! -$500")

@app.on_message(filters.command("protect"))
async def protect_cmd(client, message: Message):
    if len(message.command) < 2: return await message.reply_text("⚠️ Usage: /protect 1d")
    duration = message.command[1]
    days_map = {"1d": 1, "2d": 2, "3d": 3}
    if duration not in days_map: return
    user = get_user(message.from_user.id)
    if days_map[duration] > 1 and not user['premium']: return await message.reply_text("❌ Premium only!")
    cost = 2000 * days_map[duration]
    if user['balance'] < cost: return await message.reply_text(f"❌ You need ${cost}!")
    user['balance'] -= cost
    user['protected_until'] = time.time() + (86400 * days_map[duration])
    await message.reply_text(f"🛡️ Protected for {duration}!")

@app.on_message(filters.command("give"))
async def give_cmd(client, message: Message):
    if not message.reply_to_message or len(message.command) < 2: return await message.reply_text("Usage: /give [amount]")
    try: amount = int(message.command[1])
    except: return
    sender = get_user(message.from_user.id)
    receiver = get_user(message.reply_to_message.from_user.id)
    if sender['balance'] < amount: return await message.reply_text("❌ Low balance.")
    tax = int(amount * (0.05 if sender['premium'] else 0.10))
    sender['balance'] -= amount
    receiver['balance'] += (amount - tax)
    await message.reply_text(f"💸 Sent ${amount - tax} (Tax: ${tax})")

@app.on_message(filters.command("toprich"))
async def toprich(client, message: Message):
    top = sorted(user_db.values(), key=lambda x: x['balance'], reverse=True)[:10]
    txt = "🏆 **Top Richest Users**\n\n"
    for i, u in enumerate(top, 1): txt += f"{i}. {u['name']} - ${u['balance']}\n"
    await message.reply_text(txt)

@app.on_message(filters.command("topkill"))
async def topkill(client, message: Message):
    top = sorted(user_db.values(), key=lambda x: x['kills'], reverse=True)[:10]
    txt = "⚔️ **Top 10 Killers**\n\n"
    for i, u in enumerate(top, 1): txt += f"{i}. {u['name']} - {u['kills']} Kills\n"
    await message.reply_text(txt)

# ---------------- 3. AI CHATBOT SYSTEM (FINAL FIX) ---------------- #

def get_ai_response(user_text):
    try:
        # 1. Persona and Prompt Setup
        system = "You are Baka, a sassy and cute female Telegram bot. Reply in Hinglish (Hindi + English). Act like a real person, use emojis. User says: "
        full_prompt = f"{system} {user_text}"
        
        # 2. URL Encoding (CRITICAL FIX): Spaces must be converted to %20
        # This prevents the request from failing on text with spaces.
        encoded_prompt = urllib.parse.quote(full_prompt)
        
        # 3. Call the API
        url = f"https://text.pollinations.ai/{encoded_prompt}"
        response = requests.get(url, timeout=10) # 10 second timeout
        
        if response.status_code == 200:
            return response.text
        else:
            return "Server busy hai yaar... (API Error) 😵‍💫"
    except Exception as e:
        print(f"AI Error: {e}")
        return "Mera dimag kharab ho raha hai (Error) 😵‍💫"

# Filter: Matches TEXT that does NOT start with / or .
@app.on_message(filters.text)
async def chat_handler(client, message: Message):
    # Ignore commands manually to be safe
    if message.text.startswith("/") or message.text.startswith("."):
        return

    # Decide when to reply
    is_private = message.chat.type == "private"
    is_mentioned = message.mentioned
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == client.me.id
    
    if is_private or is_mentioned or is_reply_to_bot:
        try:
            await client.send_chat_action(message.chat.id, "typing")
            # Run AI in background so bot doesn't freeze
            reply = await asyncio.to_thread(get_ai_response, message.text)
            await message.reply_text(reply)
        except Exception as e:
            print(f"Handler Error: {e}")

# ---------------- 4. ADMIN & PAYMENT ---------------- #

@app.on_message(filters.command("pay"))
async def pay_cmd(client, message: Message):
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
    await message.reply_text(f"👤 **Your User ID:** `{message.from_user.id}`\n💬 **Chat ID:** `{message.chat.id}`")

@app.on_message(filters.command("makepremium") & filters.user(OWNER_ID))
async def make_premium(client, message: Message):
    try:
        target_id = int(message.command[1])
        if target_id not in user_db: get_user(target_id, "User")
        user_db[target_id]['premium'] = True
        await message.reply_text(f"✅ User `{target_id}` is now **Premium**! 💓")
    except: pass

@app.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def remove_premium(client, message: Message):
    try:
        target_id = int(message.command[1])
        if target_id in user_db:
            user_db[target_id]['premium'] = False
            await message.reply_text(f"💔 User `{target_id}` removed from Premium.")
    except: pass

@app.on_message(filters.command("premiumlist") & filters.user(OWNER_ID))
async def premium_list(client, message: Message):
    txt = "📋 **List of Premium Users:**\n\n"
    count = 0
    for uid, data in user_db.items():
        if data['premium']:
            count += 1
            txt += f"{count}. [{data['name']}](tg://user?id={uid}) (`{uid}`)\n"
    await message.reply_text(txt if count > 0 else "No premium users found.")

# ---------------- 5. STARTUP ---------------- #

async def check_admin(message):
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ["administrator", "creator"]
    except: return False

@app.on_message(filters.command(["ban", "mute", "unmute", "pin", "del"], prefixes=".") & filters.group)
async def admin_cmds(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    cmd = message.command[0]
    try:
        if cmd == "ban":
            await client.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
            await message.reply_text("🚫 Banned!")
        elif cmd == "mute":
            await client.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=False))
            await message.reply_text("🤐 Muted!")
        elif cmd == "unmute":
            await client.restrict_chat_member(message.chat.id, message.reply_to_message.from_user.id, ChatPermissions(can_send_messages=True))
            await message.reply_text("🗣️ Unmuted!")
        elif cmd == "pin":
            await message.reply_to_message.pin()
        elif cmd == "del":
            await message.reply_to_message.delete()
            await message.delete()
    except: pass

async def main():
    print("Bot Starting...")
    async with app:
        await app.set_bot_commands([
            BotCommand("start", "Start Bot"),
            BotCommand("help", "Help Menu"),
            BotCommand("economy", "Economy Guide"),
            BotCommand("claim", "Claim Group Bonus"),
            BotCommand("daily", "Daily Reward"),
            BotCommand("bal", "Check Balance"),
            BotCommand("rob", "Rob User"),
            BotCommand("kill", "Kill User"),
            BotCommand("revive", "Revive User"),
            BotCommand("protect", "Buy Protection"),
            BotCommand("give", "Give Money"),
            BotCommand("toprich", "Richest Users"),
            BotCommand("topkill", "Top Killers"),
            BotCommand("pay", "Buy Premium"),
        ])
        print("Bot is Alive & Commands Registered!")
        await idle()

if __name__ == "__main__":
    app.run(main())
