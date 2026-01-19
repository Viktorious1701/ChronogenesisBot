import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime

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
        self.history_dir = Path(current_dir) / 'history'

        self.output_dir.mkdir(exist_ok=True)
        self.history_dir.mkdir(exist_ok=True)

        self.engine = ChrononesisClubScraper(output_dir=str(self.output_dir))

    async def run_scrape(self, club_name):
        """Runs scraper, processes data, and saves history backup"""
        try:
            logger.info(f"🕸️ Starting scrape for {club_name}...")

            # 1. Scrape (Overwrites club_members.json)
            await self.engine.scrape_club(club_name)

            # 2. Load the data
            current_data = self._load_current_data()
            if not current_data:
                return None

            # 3. Save a backup to history folder (Silent background task)
            self._save_to_history(current_data)

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

    def _save_to_history(self, clean_data):
        """Saves a timestamped copy for long-term storage"""
        today = datetime.now().strftime('%Y-%m-%d')
        history_file = self.history_dir / f"members_{today}.json"

        # Don't overwrite if it exists, to preserve the first scrape of the day
        if not history_file.exists():
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, indent=2, ensure_ascii=False)

    def _normalize_data(self, raw_data):
        """
        Parses the strings from the website into Numbers for the bot.
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
                # Remove '+' and ',' and convert to integer
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
