import random
import asyncio
import requests
import urllib.parse
import base64
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatAction
from config import GIT_TOKEN

# --- SECURITY ENCRYPTION ---
def _decrypt(data):
    return base64.b64decode(data).decode("utf-8")

# Encrypted Endpoint (AIMLAPI)
_E_URL = "aHR0cHM6Ly9hcGkuYWltbGFwaS5jb20vY2hhdC9jb21wbGV0aW9ucw=="

# Encrypted Owner/Creator Tag (@WTF_Phantom)
_E_CREATOR = "QFdURl9QaGFudG9t"

# Encrypted Models List (Fallback System)
# 1. gpt-4o
# 2. gpt-4o-mini
# 3. meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo
_E_MODELS = [
    "Z3B0LTRv", 
    "Z3B0LTRvLW1pbmk=", 
    "bWV0YS1sbGFtYS9NZXRhLUxsYW1hLTMuMS03MEItSW5zdHJ1Y3QtVHVyYm8="
]

def ai_secure_engine(text):
    if not GIT_TOKEN:
        print("⚠️ AI Token Missing.")
        return None
    
    try:
        target_url = _decrypt(_E_URL)
        # Decrypt Owner for System Prompt
        owner_tag = _decrypt(_E_CREATOR)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GIT_TOKEN}"
        }

        # Loop through models: If one fails, try the next
        for enc_model in _E_MODELS:
            try:
                target_model = _decrypt(enc_model)
                
                # Injected Owner Tag into System Prompt securely
                sys_prompt = f"You are Baka, a sassy female bot created by {owner_tag}. Reply in Hinglish (Hindi+English). Be savage but cute. Keep replies very short (1-2 sentences max)."

                payload = {
                    "messages": [
                        {"role": "system", "content": sys_prompt}, 
                        {"role": "user", "content": text}
                    ], 
                    "model": target_model, 
                    "temperature": 0.7,
                    "max_tokens": 150
                }

                res = requests.post(target_url, headers=headers, json=payload, timeout=8)

                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
                else:
                    print(f"⚠️ Model {target_model} busy/failed ({res.status_code}), switching...")
                    continue # Try next model
                    
            except Exception as e: 
                print(f"❌ Secure AI Exception on {target_model}: {e}")
                continue # Try next model

    except Exception as e:
        print(f"❌ AI Critical Error: {e}")
        
    return None

def ai_pollinations(text):
    try:
        # Decrypt Owner for Fallback System Prompt
        owner_tag = _decrypt(_E_CREATOR)
        
        seed = random.randint(1, 9999)
        system = f"You are Baka, a sassy female Telegram bot created by {owner_tag}. Reply in Hinglish. Keep it short."
        
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

        # 1. Try Secure Engine (Multi-Model Fallback)
        response = await asyncio.to_thread(ai_secure_engine, message.text)

        # 2. Fallback to Pollinations (If all AIML models fail)
        if not response:
            response = await asyncio.to_thread(ai_pollinations, message.text)

        # 3. Final Error
        if not response:
            response = "Server busy hai yaar... baad mein aana! 😵‍💫"

        await message.reply_text(response)
