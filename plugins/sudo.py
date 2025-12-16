import os
import sys
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from config import OWNER_ID, HEROKU_API_KEY, HEROKU_APP_NAME

async def check_owner(message: Message):
    return message.from_user.id == OWNER_ID

@Client.on_message(filters.command("restart") & filters.user(OWNER_ID))
async def restart_bot(client, message):
    await message.reply_text("🔄 **Bot is restarting successful...**")
    os.execl(sys.executable, sys.executable, *sys.argv)

@Client.on_message(filters.command("logs") & filters.user(OWNER_ID))
async def get_logs(client, message):
    if not HEROKU_API_KEY or not HEROKU_APP_NAME:
        return await message.reply_text("❌ Heroku Vars Missing (HEROKU_API_KEY, HEROKU_APP_NAME)")
    
    msg = await message.reply_text("🔄 Fetching Logs...")
    try:
        headers = {
            "Accept": "application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {HEROKU_API_KEY}"
        }
        # Get Log Session
        url = f"https://api.heroku.com/apps/{HEROKU_APP_NAME}/log-sessions"
        payload = {"lines": 100, "tail": False}
        r = requests.post(url, headers=headers, json=payload)
        
        if r.status_code != 201:
            return await msg.edit_text(f"❌ Error: {r.text}")
            
        log_url = r.json()['logplex_url']
        logs = requests.get(log_url).text
        
        with open("logs.txt", "w") as f:
            f.write(logs)
            
        await message.reply_document("logs.txt", caption="📄 **Heroku Logs**")
        os.remove("logs.txt")
    except Exception as e:
        await msg.edit_text(f"❌ Exception: {e}")
