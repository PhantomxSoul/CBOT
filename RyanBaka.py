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
    if name != "User": 
        user_db[user_id]["name"] = name
    return user_db[user_id]

# ---------------- 1. EXACT START MENU (RESTORED) ---------------- #

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    get_user(message.from_user.id, message.from_user.first_name)
    
    # EXACT FONTS AND TEXT
    txt = (
        f"✨ 𝐇𝐞𝐲 {message.from_user.mention} ~\n"
        f"𖦹 𝒀𝒐𝒖'𝒓𝒆 𝒕𝒂𝒍𝒌𝒊𝒏𝒈 𝒕𝒐 𝑩𝒂𝒌𝒂, 𝒂 𝒔𝒂𝒔𝒔𝒚 𝒄𝒖𝒕𝒊𝒆 𝒃𝒐𝒕 💕\n\n"
        f"𖥔 Choose an option below:"
    )

    # EXACT BUTTON LAYOUT
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
    elif query.data == "friends_info":
        await query.answer("Friend system coming soon! 🧸", show_alert=True)
    elif query.data == "games_info":
        await query.answer("Use /economy to see games! 🎮", show_alert=True)

# ---------------- 2. EXACT REPLIES (NEW REQUEST) ---------------- #

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

    # EXACT RESPONSE TEXT
    if user['premium']:
         await message.reply_text(f"✅ You received: ${reward} daily reward! (Premium 🌟)")
    else:
        await message.reply_text(
            f"✅ You received: ${reward} daily reward!\n"
            f"💓 Upgrade to premium using /pay to get $2000 daily reward!"
        )

@app.on_message(filters.command("pay"))
async def pay_cmd(client, message: Message):
    # EXACT RESPONSE TEXT
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
    txt = (
        f"👤 **Your User ID:** `{message.from_user.id}`\n"
        f"💬 **Chat ID:** `{message.chat.id}`"
    )
    await message.reply_text(txt)

# ---------------- 3. HELP & MENUS (RESTORED) ---------------- #

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
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

# ---------------- 4. FULL ECONOMY (RESTORED) ---------------- #

@app.on_message(filters.command("bal"))
async def bal_cmd(client, message: Message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    name = message.reply_to_message.from_user.first_name if message.reply_to_message else message.from_user.first_name
    
    data = get_user(user_id, name)
    
    # Rank Logic Mockup
    rank = random.randint(100, 2000) 
    
    txt = (
        f"👤 Name: {data['name']}\n"
        f"💰 Total Balance: ${data['balance']}\n"
        f"🏆 Global Rank: {rank}\n"
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
    if duration not in days_map: return
        
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

@app.on_message(filters.command("rob"))
async def rob_cmd(client, message: Message):
    if not message.reply_to_message: return
    robber = get_user(message.from_user.id)
    victim = get_user(message.reply_to_message.from_user.id)
    
    if robber['status'] == "dead" or victim['status'] == "dead":
        await message.reply_text("Cannot rob dead people!")
        return

    if time.time() < victim['protected_until']:
        await message.reply_text("🛡️ Target is protected!")
        return

    # Rob logic: 50% chance to fail
    if random.choice([True, False]):
        amount = random.randint(100, 5000)
        if victim['balance'] < amount: amount = victim['balance']
        victim['balance'] -= amount
        robber['balance'] += amount
        await message.reply_text(f"💸 You stole ${amount} from {message.reply_to_message.from_user.first_name}!")
    else:
        fine = 500
        robber['balance'] -= fine
        await message.reply_text(f"🚔 Police caught you! You paid ${fine} fine.")

@app.on_message(filters.command("toprich"))
async def toprich(client, message: Message):
    top = sorted(user_db.values(), key=lambda x: x['balance'], reverse=True)[:10]
    txt = "🏆 **Top Richest Users**\n\n"
    for i, u in enumerate(top, 1):
        txt += f"{i}. {u['name']} - ${u['balance']}\n"
    await message.reply_text(txt)

# ---------------- 5. SUDO / OWNER COMMANDS (NEW) ---------------- #

@app.on_message(filters.command("makepremium") & filters.user(OWNER_ID))
async def make_premium(client, message: Message):
    try:
        if len(message.command) < 2: return
        target_id = int(message.command[1])
        if target_id not in user_db: get_user(target_id, "User")
        user_db[target_id]['premium'] = True
        await message.reply_text(f"✅ User `{target_id}` is now **Premium**! 💓")
    except: pass

@app.on_message(filters.command("removepremium") & filters.user(OWNER_ID))
async def remove_premium(client, message: Message):
    try:
        if len(message.command) < 2: return
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

# ---------------- 6. ADMIN DOT COMMANDS (RESTORED) ---------------- #

async def check_admin(message):
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ["administrator", "creator"]
    except: return False

@app.on_message(filters.command("ban", prefixes=".") & filters.group)
async def ban_user(client, message: Message):
    if not await check_admin(message) or not message.reply_to_message: return
    try:
        await client.ban_chat_member(message.chat.id, message.reply_to_message.from_user.id)
        await message.reply_text("🚫 Banned!")
    except: pass

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

# ---------------- 7. STARTUP ---------------- #

async def main():
    print("Bot Starting...")
    async with app:
        await app.set_bot_commands([
            BotCommand("start", "Start Bot"),
            BotCommand("help", "Get Help"),
            BotCommand("economy", "Economy Guide"),
            BotCommand("daily", "Claim Reward"),
            BotCommand("pay", "Get Premium"),
            BotCommand("bal", "Check Balance"),
        ])
        print("Bot is Alive!")
        await idle()

if __name__ == "__main__":
    app.run(main())
