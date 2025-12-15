import os

# ----------------- TELEGRAM CREDENTIALS ----------------- #
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")

# ----------------- OWNER & ADMIN ----------------- #
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

# ----------------- DATABASE & LOGGING ----------------- #
MONGO_URL = os.environ.get("MONGO_URL")
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))

# ----------------- AI API KEYS ----------------- #
GIT_TOKEN = os.environ.get("GIT_TOKEN")
