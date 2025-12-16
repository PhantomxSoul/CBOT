import random
import asyncio
import requests
import urllib.parse
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatAction
from config import GIT_TOKEN

# --- AI ENGINES ---

def ai_github(text):
    if not GIT_TOKEN:
        print("⚠️ GitHub AI Skipped: GIT_TOKEN is missing.")
        return None
    try:
        url = "https://models.inference.ai.azure.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GIT_TOKEN}"
        }
        # Short & Sassy Prompt
        payload = {
            "messages": [
                {"role": "system", "content": "You are Baka, a sassy female bot. Reply in Hinglish (Hindi+English). Be savage but cute. Keep replies very short (1-2 sentences max)."}, 
                {"role": "user", "content": text}
            ], 
            "model": "gpt-4o", 
            "temperature": 0.8,
            "max_tokens": 150
        }
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        
        if res.status_code != 200:
            print(f"❌ GitHub API Error: {res.status_code} - {res.text}")
            return None
            
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e: 
        print(f"❌ GitHub Exception: {e}")
        pass
    return None

def ai_pollinations(text):
    try:
        seed = random.randint(1, 9999)
        system = "You are Baka, a sassy female Telegram bot. Reply in Hinglish. Keep it short."
        encoded_text = urllib.parse.quote(text)
        encoded_sys = urllib.parse.quote(system)
        
        url = f"https://text.pollinations.ai/{encoded_text}?seed={seed}&model=openai&system={encoded_sys}"
        res = requests.get(url, timeout=8)
        
        if res.status_code != 200:
            print(f"❌ Pollinations API Error: {res.status_code}")
            return None

        return res.text
    except Exception as e:
        print(f"❌ Pollinations Exception: {e}") 
        pass
    return None

# --- HANDLER ---

@Client.on_message(filters.text & ~filters.regex(r"^[/\.]"))
async def chat_handler(client, message):
    is_private = message.chat.type == ChatType.PRIVATE
    is_mentioned = message.mentioned
    is_reply = message.reply_to_message and message.reply_to_message.from_user.id == client.me.id
    
    if is_private or is_mentioned or is_reply:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
        
        # 1. Try GitHub
        response = await asyncio.to_thread(ai_github, message.text)
        
        # 2. Try Pollinations
        if not response:
            response = await asyncio.to_thread(ai_pollinations, message.text)
            
        # 3. Final Error
        if not response:
            response = "Server busy hai yaar... baad mein aana! 😵‍💫"
            
        await message.reply_text(response)
