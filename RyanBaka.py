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
from pyrogram import Client, idle
from pyrogram.types import BotCommand

# IMPORT SETTINGS FROM CONFIG
from config import API_ID, API_HASH, BOT_TOKEN, MONGO_URL, LOG_CHANNEL_ID

# IMPORT HELPER TEXTS
# NOTE: Ensure helper.py is inside the 'plugins' folder!
from plugins.helper import START_TEXT

# INITIALIZE CLIENT
# 'plugins=dict(root="plugins")' automatically loads all files in the plugins folder
app = Client(
    "baka_master", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins") 
)

# ---------------- DATABASE CONNECTION ---------------- #
if not MONGO_URL:
    print("❌ CRITICAL: MONGO_URL MISSING. Bot cannot start.")
    exit()

mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo.baka_bot

# --- HELPER FUNCTIONS ---
async def log_deployment():
    if LOG_CHANNEL_ID:
        try:
            # FIX: FORCE BOT TO FETCH CHAT INFO FIRST
            # This solves the "Peer id invalid" error on Heroku restarts
            try:
                await app.get_chat(LOG_CHANNEL_ID)
            except:
                pass 

            await app.send_message(
                LOG_CHANNEL_ID, 
                f"✅ **Bot Deployed Successfully!**\n📅 {datetime.now()}\n🤖 Version: Modular v5.0 (Final)",
                disable_web_page_preview=True
            )
            print("✅ Deployment Log Sent.")
        except Exception as e:
            print(f"❌ LOG ERROR: Could not send deployment log. Reason: {e}")

# ---------------- STARTUP LOGIC ---------------- #

async def main():
    print("Bot Starting...")
    
    # 1. Start the Bot Client
    await app.start()
    print("Bot Client Started.")
    
    # 2. Send Deployment Log
    await log_deployment()
    
    # 3. Set Bot Commands (Menu)
    commands = [
        ("start", "Talk to Baka"), 
        ("pay", "Buy premium access"), 
        ("check", "Check protection"),
        ("daily", "Claim $1000 daily reward"), 
        ("claim", "Add baka in groups and claim"),
        ("own", "Make your own sticker pack"), 
        ("help", "Show admin commands"),
        ("open", "Open gaming commands"), 
        ("close", "Close gaming commands"),
        ("music", "Get the random music list"), 
        ("couples", "Choose random couples"),
        ("crush", "Reply to someone"), 
        ("love", "Reply to someone"), 
        ("look", "Reply to someone"),
        ("brain", "Reply to someone"), 
        ("stupid_meter", "Reply to someone"),
        ("slap", "Reply to someone"), 
        ("punch", "Reply to someone"), 
        ("bite", "Reply to someone"),
        ("kiss", "Reply to someone"), 
        ("hug", "Reply to someone"), 
        ("truth", "Picks a truth"),
        ("dare", "Picks a dare"), 
        ("puzzle", "Picks a puzzle"), 
        ("tr", "Translate any text"),
        ("detail", "Know about past names/usernames"), 
        ("id", "Reply to someone"),
        ("adminlist", "Check adminlist"), 
        ("owner", "Tag group owner"),
        ("bal", "See ur/ur friend's balance"), 
        ("rob", "Reply to someone"),
        ("kill", "Reply to someone"), 
        ("revive", "Use with or without reply"),
        ("protect", "Protect urself from robbery"), 
        ("give", "Give money to the replied user"),
        ("toprich", "See top 10 users globally"), 
        ("topkill", "See top 10 killers globally"),
        ("item", "Use with or without reply"), 
        ("items", "Check all available items"),
        ("gift", "Gift a item"), 
        ("economy", "See all economy commands")
    ]
    try:
        await app.set_bot_commands([BotCommand(c, d) for c, d in commands])
        print("✅ Bot Commands Set Successfully.")
    except Exception as e:
        print(f"⚠️ Failed to set commands: {e}")

    print("Bot is Alive and Running!")
    
    # 4. Keep the bot running
    await idle()
    
    # 5. Stop the bot gracefully
    await app.stop()

if __name__ == "__main__":
    app.run(main())
