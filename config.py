import os
from dotenv import load_dotenv

load_dotenv()

# Discord Secrets
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Server Configuration {Guild_ID: Channel_ID}
# converting env strings to integers
try:
    target_guild = int(os.getenv('GUILD_ID'))
    target_channel = int(os.getenv('CHANNEL_ID'))
    NOTIFICATION_CHANNELS = {target_guild: target_channel}
except (TypeError, ValueError):
    print("⚠️ WARNING: GUILD_ID or CHANNEL_ID in .env are not valid numbers.")
    NOTIFICATION_CHANNELS = {}

# Bot Settings
NOTIFICATION_TIME = os.getenv('NOTIFICATION_TIME', '08:00')
CLUB_NAME = os.getenv('SCRAPE_CLUB_NAME', 'Uchoom')
TIMEZONE = 'Asia/Ho_Chi_Minh'

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
