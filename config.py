import os

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_USERNAME = os.environ.get("BOT_USERNAME")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
MONGO_URL = os.environ.get("MONGO_URL")
LOG_CHANNEL_ID = int(os.environ.get("LOG_CHANNEL_ID", "0"))
GIT_TOKEN = os.environ.get("GIT_TOKEN")
HEROKU_API_KEY = os.environ.get("HEROKU_API_KEY")
HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
