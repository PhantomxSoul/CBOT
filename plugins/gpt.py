import random
import asyncio
import requests
import urllib.parse
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatAction
from config import GIT_TOKEN

# --- AI ENGINES ---

def ai_github(text):
    if not GIT_TOKEN: return None
    try:
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {GIT_TOKEN}"}
        payload = {
            "messages": [
                {"role": "system", "content": "You are Baka, a sassy female bot. Reply in Hinglish (Hindi+English). Be savage, cute, and use emojis."}, 
                {"role": "user", "content": text}
            ], 
            "model": "gpt-4o", 
            "temperature": 0.8
        }
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200: 
            return res.json()["choices"][0]["message"]["content"]
    except: 
        pass
    return None

def ai_pollinations(text):
    try:
        # Anti-Cache Seed
        seed = random.randint(1, 9999)
        system = "You are Baka, a sassy female Telegram bot. Reply in Hinglish."
        encoded_text = urllib.parse.quote(text)
        encoded_system = urllib.parse.quote(system)
        
        url = f"https://text.pollinations.ai/{encoded_text}?seed={seed}&model=openai&system={encoded_system}"
        res = requests.get(url, timeout=8)
        
        if res.status_code == 200: 
            return res.text
    except: 
        pass
    return None

# --- HANDLER ---

@Client.on_message(filters.text & ~filters.regex(r"^[/\.]"))
async def chat_handler(client, message):
    # Logic: Reply in Private OR if Mentioned OR if Replying to Bot
    is_private = message.chat.type == ChatType.PRIVATE
    is_mentioned = message.mentioned
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == client.me.id
    
    if is_private or is_mentioned or is_reply:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        response = await asyncio.to_thread(ai_github, message.text)
        
        # 2. Fallback to Pollinations (Unstoppable)
        if not response:
            response = await asyncio.to_thread(ai_pollinations, message.text)
            
        # 3. Final Error
        if not response:
            response = "Server busy hai yaar... thodi der baad baat karte hain! 😵‍💫"
            
        await message.reply_text(response)
