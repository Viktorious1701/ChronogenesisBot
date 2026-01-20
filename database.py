import sqlite3
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger('discord_bot.database')

class DatabaseManager:
    def __init__(self, db_name="club_data.db"):
        self.db_path = Path(__file__).parent / db_name
        self.conn = sqlite3.connect(self.db_path)
        # Allow accessing columns by name (row['fans'])
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """Create the tables if they don't exist"""
        c = self.conn.cursor()
        
        # 1. Members Table: Keeps track of who is who (ID is constant, Name changes)
        c.execute('''
            CREATE TABLE IF NOT EXISTS members (
                friend_id TEXT PRIMARY KEY,
                current_name TEXT,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # 2. Snapshots Table: The history of every scrape
        c.execute('''
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                friend_id TEXT,
                timestamp DATETIME,
                total_fans INTEGER,
                daily_gain_ingame INTEGER,
                FOREIGN KEY(friend_id) REFERENCES members(friend_id)
            )
        ''')
        
        self.conn.commit()

    def save_snapshot(self, scraper_data):
        """
        Takes the list from the scraper and saves it to DB.
        Auto-detects new members and name changes.
        """
        c = self.conn.cursor()
        timestamp = datetime.now().isoformat()
        
        try:
            # 1. Mark everyone as inactive first (we will re-activate those we see)
            c.execute("UPDATE members SET is_active = 0")
            
            for m in scraper_data:
                f_id = m['id']
                name = m['name']
                fans = m['fans']
                gain = m['gain']
                
                # 2. Update/Insert Member
                c.execute('''
                    INSERT INTO members (friend_id, current_name, is_active)
                    VALUES (?, ?, 1)
                    ON CONFLICT(friend_id) DO UPDATE SET 
                        current_name = excluded.current_name,
                        is_active = 1
                ''', (f_id, name))
                
                # 3. Insert Snapshot
                c.execute('''
                    INSERT INTO snapshots (friend_id, timestamp, total_fans, daily_gain_ingame)
                    VALUES (?, ?, ?, ?)
                ''', (f_id, timestamp, fans, gain))
                
            self.conn.commit()
            logger.info(f"💾 Database updated with {len(scraper_data)} records.")
            
        except Exception as e:
            logger.error(f"❌ Database error: {e}")
            self.conn.rollback()

    def get_leaderboard(self, start_date_iso):
        """Calculates GAIN from a specific start date until NOW."""
        c = self.conn.cursor()
        query = '''
        WITH 
        CurrentState AS (
            SELECT friend_id, total_fans as end_fans
            FROM snapshots 
            WHERE id IN (SELECT MAX(id) FROM snapshots GROUP BY friend_id)
        ),
        BaselineState AS (
            SELECT s.friend_id, s.total_fans as start_fans
            FROM snapshots s
            JOIN (
                SELECT friend_id, MIN(timestamp) as min_time
                FROM snapshots 
                WHERE timestamp >= ? 
                GROUP BY friend_id
            ) first_s ON s.friend_id = first_s.friend_id AND s.timestamp = first_s.min_time
        )
        
        SELECT 
            m.current_name,
            (curr.end_fans - base.start_fans) as period_gain
        FROM members m
        JOIN CurrentState curr ON m.friend_id = curr.friend_id
        JOIN BaselineState base ON m.friend_id = base.friend_id
        WHERE m.is_active = 1
        ORDER BY period_gain DESC
        '''
        c.execute(query, (start_date_iso,))
        return [dict(row) for row in c.fetchall()]

    # --- NEW FUNCTION FOR ADMIN LOOKUP ---
    def lookup_member(self, name_query):
        """
        Finds a member by partial name match and calculates lifetime stats.
        """
        c = self.conn.cursor()
        
        # 1. Find the Member ID (Case insensitive search)
        c.execute("SELECT friend_id, current_name, joined_at FROM members WHERE current_name LIKE ? LIMIT 1", (f"%{name_query}%",))
        member = c.fetchone()
        
        if not member:
            return None
            
        f_id = member['friend_id']
        name = member['current_name']
        joined = member['joined_at']
        
        # 2. Get First Ever Snapshot (The Baseline)
        c.execute("SELECT total_fans, timestamp FROM snapshots WHERE friend_id = ? ORDER BY timestamp ASC LIMIT 1", (f_id,))
        first = c.fetchone()
        
        # 3. Get Latest Snapshot (Current Status)
        c.execute("SELECT total_fans, timestamp FROM snapshots WHERE friend_id = ? ORDER BY timestamp DESC LIMIT 1", (f_id,))
        last = c.fetchone()
        
        if not first or not last:
            return None
            
        # Calculate Stats
        original_fans = first['total_fans']
        current_fans = last['total_fans']
        accumulated = current_fans - original_fans
        
        return {
            'name': name,
            'id': f_id,
            'joined': joined,
            'first_seen': first['timestamp'],
            'last_seen': last['timestamp'],
            'original_fans': original_fans,
            'current_fans': current_fans,
            'accumulated_fans': accumulated
        }