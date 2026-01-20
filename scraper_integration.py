import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# --- DATABASE IMPORT ---
# We import the DatabaseManager to handle long-term storage
from database import DatabaseManager

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
scraper_path = os.path.join(current_dir, 'chronogenesis_scraper')
sys.path.append(scraper_path)

try:
    from scraper import ChrononesisClubScraper
except ImportError:
    raise

logger = logging.getLogger('discord_bot')


class ChrononesisClubScraperBot:
    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # 1. Initialize the Scraper Engine
        self.engine = ChrononesisClubScraper(output_dir=str(self.output_dir))
        
        # 2. Initialize the Database Manager
        # This creates 'club_data.db' if it doesn't exist
        self.db = DatabaseManager()

    async def run_scrape(self, club_name):
        """Runs scraper, processes data, and saves to Database"""
        try:
            logger.info(f"🕸️ Starting scrape for {club_name}...")

            # 1. Run the Scraper (Overwrites club_members.json)
            await self.engine.scrape_club(club_name)

            # 2. Load the fresh data from the file
            current_data = self._load_current_data()
            
            if not current_data:
                logger.warning("⚠️ Scrape finished but no data found.")
                return None

            # 3. SAVE TO DATABASE (The Time Machine)
            # This allows us to calculate monthly/weekly rankings later
            logger.info("💾 Saving snapshot to SQLite Database...")
            self.db.save_snapshot(current_data)

            return current_data

        except Exception as e:
            logger.error(f"❌ Scraper execution failed: {e}", exc_info=True)
            return None

    def _load_current_data(self):
        target_file = self.output_dir / 'club_members.json'
        if not target_file.exists():
            return []

        with open(target_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return self._normalize_data(data)

    def _normalize_data(self, raw_data):
        """
        Parses the strings from the website into Numbers for the bot/database.
        """
        members_list = raw_data.get('members', [])
        cleaned = []

        for m in members_list:
            # 1. Clean Total Fans (e.g., "58,844,280")
            fans_str = str(m.get('total_fans', '0'))
            try:
                fans_int = int(fans_str.replace(',', '').replace('+', ''))
            except ValueError:
                fans_int = 0

            # 2. Clean Fan Change (e.g., "+1,440,104")
            # This is the GREEN text from the website
            change_str = str(m.get('fan_change', '0'))
            try:
                change_int = int(change_str.replace(',', '').replace('+', ''))
            except ValueError:
                change_int = 0

            cleaned.append({
                'name': m.get('name', 'Unknown'),
                'id': m.get('friend_id', 'N/A'),
                'fans': fans_int,          # Total Fans
                'gain': change_int,        # Daily Gain (From Website)
                'rank': m.get('rank', 'N/A'),
                'role': m.get('role', 'Member'),
                'last_login': m.get('last_login', '-')
            })

        return cleaned