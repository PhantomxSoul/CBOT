# Copyright (c) 2025 Telegram:- @WTF_Phantom <DevixOP>
# Location: Supaul, Bihar 
#
# All rights reserved.
#
# This code is the intellectual property of @WTF_Phantom.
# You are not allowed to copy, modify, redistribute, or use this
# code for commercial or personal projects without explicit permission.
#
# Allowed:
# - Forking for personal learning
# - Submitting improvements via pull requests
#
# Not Allowed:
# - Claiming this code as your own
# - Re-uploading without credit or permission
# - Selling or using commercially
#
# Contact for permissions:
# Email: king25258069@gmail.com

import os
import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatType
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Message, 
    BotCommand
)
# IMPORTS
from config import API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME, MONGO_URL, LOG_CHANNEL_ID
from helper import START_TEXT, HELP_TEXT

# CLIENT SETUP
app = Client(
    "baka_master", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins") # Automatically loads gpt.py, inline.py, games.py, admin.py
)

# DATABASE
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot
users_col = db.users

async def get_user(user_id, name="User"):
    user = await users_col.find_one({"_id": user_id})
    if not user:
        user = {
            "_id": user_id, "name": name, "balance": 0, "status": "alive",
            "kills": 0, "premium": False, "last_daily": 0, "protected_until": 0,
            "items": {} 
        }
        await users_col.insert_one(user)
    return user

async def log_event(text):
    if LOG_CHANNEL_ID != 0:
        try:
            await app.send_message(LOG_CHANNEL_ID, text, disable_web_page_preview=True)
        except Exception as e:
            print(f"❌ LOG ERROR: {e}")

# ---------------- COMMANDS ---------------- #

@app.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    await get_user(message.from_user.id, message.from_user.first_name)
    
    if message.chat.type == ChatType.PRIVATE:
        log_text = (
            f"🚀 **User Started Bot**\n"
            f"👤 {message.from_user.mention}\n"
            f"🆔 `{message.from_user.id}`"
        )
        await log_event(log_text)

    # Use text from helper.py
    txt = START_TEXT.format(mention=message.from_user.mention)
    
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Talk to Baka 💬", callback_data="talk_info")],
        [InlineKeyboardButton("✨ Friends 🧸", url="https://t.me/ShreyaBotSupport"),
         InlineKeyboardButton("✨ Games 🎮", callback_data="games_info")],
        [InlineKeyboardButton("➕ Add me to your group 👥", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
    ])
    await message.reply_text(text=txt, reply_markup=buttons)

@app.on_message(filters.command("help"))
async def help_cmd(client, message: Message):
    await message.reply_text(HELP_TEXT)

@app.on_message(filters.command("id"))
async def id_cmd(client, message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    await message.reply_text(f"🆔 **ID:** `{target.id}`")

# ---------------- STARTUP ---------------- #

async def main():
    print("Bot Starting...")
    await app.start()
    
    await log_event(f"✅ **Bot Deployed Successfully!**\n📅 {datetime.now()}")
    
    commands = [
        ("start", "Talk to Baka"), ("pay", "Buy premium access"), ("check", "Check protection"),
        ("daily", "Claim $1000 daily reward"), ("claim", "Add baka in groups and claim"),
        ("own", "Make your own sticker pack"), ("help", "Show admin commands"),
        ("open", "Open gaming commands"), ("close", "Close gaming commands"),
        ("music", "get the random music list"), ("couples", "Choose random couples"),
        ("crush", "Reply to someone"), ("love", "Reply to someone"), ("look", "Reply to someone"),
        ("brain", "Reply to someone"), ("stupid_meter", "Reply to someone"),
        ("slap", "Reply to someone"), ("punch", "Reply to someone"), ("bite", "Reply to someone"),
        ("kiss", "Reply to someone"), ("hug", "Reply to someone"), ("truth", "Picks a truth"),
        ("dare", "Picks a dare"), ("puzzle", "Picks a puzzle"), ("tr", "Translate any text"),
        ("detail", "Know about past names/usernames"), ("id", "Reply to someone"),
        ("adminlist", "Check adminlist"), ("owner", "Tag group owner"),
        ("bal", "see ur/ur friend's balance"), ("rob", "Reply to someone"),
        ("kill", "Reply to someone"), ("revive", "Use with or without reply"),
        ("protect", "Protect urself from robbery"), ("give", "Give money to the replied user"),
        ("toprich", "See top 10 users globally"), ("topkill", "See top 10 killers globally"),
        ("item", "Use with or without reply"), ("items", "Check all available items"),
        ("gift", "Gift a item"), ("economy", "See all economy commands")
    ]
    await app.set_bot_commands([BotCommand(c, d) for c, d in commands])
    print("Bot is Alive!")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())
