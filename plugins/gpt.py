import random
import asyncio
import requests
import urllib.parse
import base64
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatAction
from config import GIT_TOKEN

# --- SECURITY ENCRYPTION ---
# These strings are encrypted so no one knows the real provider
def _decrypt(data):
    return base64.b64decode(data).decode("utf-8")

# Encrypted Endpoint (AIMLAPI)
_E_URL = "aHR0cHM6Ly9hcGkuYWltbGFwaS5jb20vY2hhdC9jb21wbGV0aW9ucw=="
# Encrypted Model (gpt-4o)
_E_MOD = "Z3B0LTRv"

# --- AI ENGINES ---

def ai_secure_engine(text):
    if not GIT_TOKEN:
        print("⚠️ AI Token Missing.")
        return None
    try:
        # Decrypting credentials at runtime
        target_url = _decrypt(_E_URL)
        target_model = _decrypt(_E_MOD)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GIT_TOKEN}"
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": "You are Baka, a sassy female bot. Reply in Hinglish (Hindi+English). Be savage but cute. Keep replies very short (1-2 sentences max)."}, 
                {"role": "user", "content": text}
            ], 
            "model": target_model, 
            "temperature": 0.7,
            "max_tokens": 150
        }
        
        res = requests.post(target_url, headers=headers, json=payload, timeout=10)
        
        if res.status_code != 200:
            print(f"❌ Secure AI Error: {res.status_code}")
            return None
            
        return res.json()["choices"][0]["message"]["content"]
    except Exception as e: 
        print(f"❌ Secure AI Exception: {e}")
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
            return None

        return res.text
    except: 
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
        
        # 1. Try Secure Engine (Encrypted Provider)
        response = await asyncio.to_thread(ai_secure_engine, message.text)
        
        # 2. Fallback to Pollinations
        if not response:
            response = await asyncio.to_thread(ai_pollinations, message.text)
            
        # 3. Final Error
        if not response:
            response = "Server busy hai yaar... baad mein aana! 😵‍💫"
            
        await message.reply_text(response)
