import os
import logging
import random
from datetime import datetime, timedelta
import asyncio

# Third-party imports
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from pymongo import MongoClient
import certifi

# --- CONFIGURATION ---
# Get these from Heroku Environment Variables
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# --- DATABASE SETUP ---
# Connect to MongoDB Atlas
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['bakabot_db']
users_collection = db['users']

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- CONSTANTS & ART ---
HEADER_ART = "◄❥͜͡⃟⃝💔꯭᪳𝄄─𝐃꯭𝐄꯭𝐀꯭𝐃<꯭/꯭᪵>𝐔꯭𝐒𝐄꯭𝐑─𝄄꯭➤⃝ ⃝⃪⃕☠️"
BOT_NAME = "🫧 ʙᴀᴋᴀ ×͜࿐"
REVIVE_COST = 500
PROTECT_1D_COST = 1000
PROTECT_2D_COST = 1800
REGISTER_BONUS = 5000

# --- HELPER FUNCTIONS ---

def get_user(user_id):
    return users_collection.find_one({"user_id": user_id})

def create_user(user_id, first_name):
    if get_user(user_id):
        return False
    
    new_user = {
        "user_id": user_id,
        "name": first_name,
        "balance": REGISTER_BONUS,
        "kills": 0,
        "status": "alive",
        "protection_expiry": datetime.utcnow(),
        "registered_at": datetime.utcnow()
    }
    users_collection.insert_one(new_user)
    return True

def is_protected(user_data):
    if "protection_expiry" not in user_data:
        return False
    return user_data["protection_expiry"] > datetime.utcnow()

def format_money(amount):
    return f"${amount:,}"

# --- COMMAND HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        f"{HEADER_ART}:\n"
        f"/start\n\n"
        f"{BOT_NAME}:\n"
        f"✨ 𝐇𝐞𝐲 {update.effective_user.first_name} ~\n"
        f"𖦹 𝒀𝒐𝒖'𝒓𝒆 𝒕𝒂𝒍𝒌𝒊𝒏𝒈 𝒕𝒐 𝑩𝒂𝒌𝒂, 𝒂 𝒔𝒂𝒔𝒔𝒚 𝒄𝒖𝒕𝒊𝒆 𝒃𝒐𝒕 💕\n\n"
        f"𖥔 Choose an option below:\n"
        f"/register - Get {format_money(REGISTER_BONUS)} bonus!\n"
        f"/bal - Check stats & rank\n"
        f"/kill (reply to user) - Kill them\n"
        f"/rob (reply or amount) - Rob them\n"
        f"/protect 1d - Buy shield\n"
        f"/revive - Come back to life"
    )
    await update.message.reply_text(msg)

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    success = create_user(user.id, user.first_name)
    
    if success:
        msg = (
            f"{HEADER_ART}:\n"
            f"/register\n\n"
            f"{BOT_NAME}:\n"
            f"🎉 Registration successful! +{format_money(REGISTER_BONUS)} added 💸"
        )
    else:
        msg = (
            f"{HEADER_ART}:\n"
            f"/register\n\n"
            f"{BOT_NAME}:\n"
            f"✨ You are already registered !!"
        )
    await update.message.reply_text(msg)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    
    if not user_data:
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ You need to /register first!")
        return

    # Calculate Global Rank
    rank = users_collection.count_documents({"balance": {"$gt": user_data["balance"]}}) + 1
    
    msg = (
        f"{HEADER_ART}:\n"
        f"/bal\n\n"
        f"{BOT_NAME}:\n"
        f"👤 Name: {user_data['name']}\n"
        f"💰 Total Balance: {format_money(user_data['balance'])}\n"
        f"🏆 Global Rank: {rank}\n"
        f"❤️ Status: {user_data['status']}\n"
        f"⚔️ Kills: {user_data['kills']}"
    )
    await update.message.reply_text(msg)

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    if not user_data:
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ /register first!")
        return

    if not context.args:
        await update.message.reply_text(
            f"{HEADER_ART}:\n/protect\n\n{BOT_NAME}:\n⚠️ Usage: /protect 1d or /protect 2d"
        )
        return

    duration = context.args[0].lower()
    cost = 0
    time_add = timedelta(0)

    if duration == '1d':
        cost = PROTECT_1D_COST
        time_add = timedelta(days=1)
    elif duration == '2d':
        cost = PROTECT_2D_COST
        time_add = timedelta(days=2)
    else:
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ Invalid duration.")
        return

    if is_protected(user_data):
        await update.message.reply_text(f"{BOT_NAME}: 🛡️ You are already protected!")
        return

    if user_data['balance'] < cost:
        await update.message.reply_text(f"{BOT_NAME}: ❌ You need {format_money(cost)}!")
        return

    # Apply protection
    new_expiry = datetime.utcnow() + time_add
    users_collection.update_one(
        {"user_id": user_data["user_id"]},
        {
            "$inc": {"balance": -cost},
            "$set": {"protection_expiry": new_expiry}
        }
    )

    await update.message.reply_text(
        f"{HEADER_ART}:\n/protect {duration}\n\n{BOT_NAME}:\n🛡️ You are now protected for {duration}."
    )

async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    if not user_data:
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ /register first!")
        return

    if user_data['status'] == 'alive':
        await update.message.reply_text(f"{BOT_NAME}: ✨ You are already alive!")
        return

    if user_data['balance'] < REVIVE_COST:
        await update.message.reply_text(
            f"{HEADER_ART}:\n/revive\n\n{BOT_NAME}:\n❌ You need {format_money(REVIVE_COST)} to revive, but you have only {format_money(user_data['balance'])}"
        )
        return

    users_collection.update_one(
        {"user_id": user_data["user_id"]},
        {
            "$inc": {"balance": -REVIVE_COST},
            "$set": {"status": "alive"}
        }
    )

    await update.message.reply_text(
        f"{HEADER_ART}:\n/revive\n\n{BOT_NAME}:\n❤️ You revived yourself! -{format_money(REVIVE_COST)}"
    )

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    attacker = get_user(update.effective_user.id)
    if not attacker:
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ /register first!")
        return
    
    if attacker['status'] == 'dead':
        await update.message.reply_text(f"{BOT_NAME}: 💀 You are dead! /revive first.")
        return

    target_msg = update.message.reply_to_message
    if not target_msg:
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ Reply to the user you want to kill!")
        return

    target_id = target_msg.from_user.id
    target = get_user(target_id)

    if not target:
        await update.message.reply_text(f"{BOT_NAME}: ❌ They haven't registered yet.")
        return

    if target['user_id'] == attacker['user_id']:
        await update.message.reply_text(f"{BOT_NAME}: 🤔 Suicidal?")
        return

    if target['status'] == 'dead':
        await update.message.reply_text(f"{BOT_NAME}: ⚰️ They are already dead!")
        return

    if is_protected(target):
        await update.message.reply_text(f"{BOT_NAME}: 🛡️ They are protected!")
        return

    # EXECUTE KILL
    users_collection.update_one({"user_id": target["user_id"]}, {"$set": {"status": "dead"}})
    users_collection.update_one({"user_id": attacker["user_id"]}, {"$inc": {"kills": 1}})

    await update.message.reply_text(
        f"{HEADER_ART}:\n/kill\n\n{BOT_NAME}:\n🔪 You KILLED {target['name']}! 🩸"
    )

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    robber = get_user(update.effective_user.id)
    if not robber:
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ /register first!")
        return

    if robber['status'] == 'dead':
        await update.message.reply_text(f"{BOT_NAME}: 💀 You are dead!")
        return

    target_msg = update.message.reply_to_message
    if not target_msg:
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ Reply to the user you want to rob!")
        return

    # Parse amount
    try:
        amount = int(context.args[0])
    except (IndexError, ValueError):
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ Usage: /rob <amount> (replying to user)")
        return

    if amount <= 0:
        await update.message.reply_text(f"{BOT_NAME}: ⚠️ Invalid amount.")
        return

    target = get_user(target_msg.from_user.id)
    if not target:
        await update.message.reply_text(f"{BOT_NAME}: ❌ They haven't registered.")
        return

    if target['user_id'] == robber['user_id']:
        return

    if target['status'] == 'dead':
        await update.message.reply_text(f"{BOT_NAME}: ⚰️ Can't rob the dead.")
        return

    if is_protected(target):
        await update.message.reply_text(f"{BOT_NAME}: 🛡️ They are protected!")
        return

    if target['balance'] < amount:
        await update.message.reply_text(f"{BOT_NAME}: 📉 They are too poor.")
        return

    # Robbery Chance (50%)
    if random.choice([True, False]):
        users_collection.update_one({"user_id": target["user_id"]}, {"$inc": {"balance": -amount}})
        users_collection.update_one({"user_id": robber["user_id"]}, {"$inc": {"balance": amount}})
        await update.message.reply_text(
            f"{HEADER_ART}:\n/rob\n\n{BOT_NAME}:\n💰 You stole {format_money(amount)} from {target['name']}!"
        )
    else:
        # Fine penalty
        fine = int(amount * 0.1)
        users_collection.update_one({"user_id": robber["user_id"]}, {"$inc": {"balance": -fine}})
        await update.message.reply_text(
            f"{HEADER_ART}:\n/rob\n\n{BOT_NAME}:\n🚔 Police caught you! You paid {format_money(fine)} bribe."
        )

# --- MAIN ---

if __name__ == '__main__':
    if not TOKEN:
        print("Error: BOT_TOKEN not found.")
        exit(1)
        
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("register", register))
    application.add_handler(CommandHandler("bal", balance))
    application.add_handler(CommandHandler("protect", protect))
    application.add_handler(CommandHandler("revive", revive))
    application.add_handler(CommandHandler("kill", kill))
    application.add_handler(CommandHandler("rob", rob))

    print("Bot is running...")
    application.run_polling()
