import os
from dotenv import load_dotenv

load_dotenv()

# API Credentials
API_ID = int(os.getenv("API_ID", "12345"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
SESSION_NAME = os.getenv("SESSION_NAME", "your_user_session_string")

# Metadata & Links
OWNER_ID = int(os.getenv("OWNER_ID", "12345678"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "YourUsername")
SUPPORT_GROUP = os.getenv("SUPPORT_GROUP", "https://t.me/YourGroup")
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/YourChannel")
# Database (In-Memory for this example)
afk_users = {}  # {user_id: reason}
# Inside config.py
queue = {}  # Format: {chat_id: [song1, song2, ...]}
playing = {} # Format: {chat_id: current_song_info}
