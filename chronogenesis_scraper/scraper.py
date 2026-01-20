"""
Club scraper for chronogenesis.net
Extracts member data from Uma Musume club profiles
"""

import asyncio
import os
from pathlib import Path
import nodriver as uc
from bs4 import BeautifulSoup
import json
import pandas as pd
from datetime import datetime


class ChrononesisClubScraper:
    """
    Fixed scraper with proper wait strategy for JavaScript-loaded content
    """

    def __init__(self, output_dir='output'):
        self.browser = None
        self.page = None
        self.output_dir = Path(output_dir)

        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)

        self.session_data = {
            'last_visit': None,
            'requests_made': 0,
            'total_members': 0,
            'output_dir': str(self.output_dir)
        }

    async def initialize_browser(self):
        """Launch browser with stealth settings"""
        print("🚀 Initializing Nodriver browser (stealth mode)...")
        self.browser = await uc.start(headless=False)
        print("✅ Browser initialized")
        return self.browser

    async def create_session(self):
        """Create a browser session"""
        if not self.browser:
            await self.initialize_browser()

        self.page = await self.browser.get('about:blank')
        print("✅ Session created")
        return self.page

    async def navigate_to_page(self, url, max_wait=30):
        """Navigate to page and WAIT for member table to appear"""
        if not self.page:
            await self.create_session()

        print(f"📖 Navigating to {url}...")

        try:
            await self.page.get(url)
            print("⏳ Page shell loaded. Now waiting for JavaScript to render data...")

            # Step 1: Wait for Cloudflare
            print("   Step 1: Waiting for Cloudflare (3 seconds)...")
            await asyncio.sleep(3)

            # Step 2: Wait for table to appear with timeout
            print("   Step 2: Waiting for member table to appear (up to 15 seconds)...")
            try:
                await self.page.wait_for_selector('table.club-member-table', timeout=7000)
                print("   ✅ Table appeared!")
            except Exception as e:
                print(f"   ⚠️ Table selector timeout: {e}")
                print("   Continuing anyway with extra wait...")
                await asyncio.sleep(10)

            # Step 3: Wait for table rows to populate
            print("   Step 3: Waiting for rows to populate (up to 10 seconds)...")
            try:
                await self.page.wait_for_selector('table.club-member-table tbody tr', timeout=10000)
                print("   ✅ Member rows appeared!")
            except Exception as e:
                print(f"   ⚠️ Rows timeout: {e}")
                await asyncio.sleep(8)

            # Step 4: Extra buffer for all content to render
            print("   Step 4: Final render buffer (5 seconds)...")
            await asyncio.sleep(5)

            print("✅ Page fully loaded with all data!")
            self.session_data['last_visit'] = datetime.now().isoformat()
            self.session_data['requests_made'] += 1
            return self.page

        except Exception as e:
            print(f"❌ Error navigating: {e}")
            return None

    async def extract_club_data(self):
        """Extract club member data from the page"""
        if not self.page:
            print("❌ No active page")
            return None

        print("🔍 Extracting club data...")

        try:
            html_content = await self.page.get_content()
            soup = BeautifulSoup(html_content, 'html.parser')

            all_text = soup.get_text()
            print(f"\n📊 Page stats:")
            print(f"   HTML size: {len(html_content)} characters")
            print(f"   Text size: {len(all_text)} characters")

            if 'Uchoom' in all_text:
                print("   ✅ Found 'Uchoom' - data loaded!")
            else:
                print("   ⚠️ 'Uchoom' not found - might need more wait time")
                # Save debug HTML
                debug_path = self.output_dir / 'debug_page.html'
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"   Saved debug HTML to {debug_path}")

            member_data = self.parse_member_table(soup)

            return {
                'html_size': len(html_content),
                'members': member_data,
                'timestamp': datetime.now().isoformat(),
                'success': len(member_data) > 0
            }

        except Exception as e:
            print(f"❌ Error extracting data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def parse_member_table(self, soup):
        """Parse member data with correct field extraction"""
        members = []

        # Find the table
        table = soup.find('table', class_='club-member-table')
        if not table:
            print("   ⚠️ No member table found - trying to find what's on page...")
            all_divs = soup.find_all('div')
            print(f"      Found {len(all_divs)} divs")
            return members

        tbody = table.find('tbody')
        if not tbody:
            print("   ⚠️ No tbody found in table")
            return members

        rows = tbody.find_all('tr', class_='club-member-row-container')
        print(f"   Found {len(rows)} member rows")

        if len(rows) == 0:
            print("   ⚠️ No member rows found - table might still be loading")
            # Debug: print what's in the tbody
            tbody_text = tbody.get_text()
            print(
                f"      tbody text content (first 200 chars): {tbody_text[:200]}")
            return members

        for i, row in enumerate(rows):
            try:
                # Get the row class to determine role
                row_classes = row.get('class', [])
                role = 'Member'
                if 'leader' in row_classes:
                    role = 'Leader'
                elif 'sub-leader' in row_classes:
                    role = 'Officer'

                # Get all cells
                cells = row.find_all('td')

                if len(cells) < 4:
                    print(
                        f"   ⚠️ Row {i} has only {len(cells)} cells, skipping")
                    continue

                # ===== CELL 1: Profile Info =====
                profile_cell = cells[0]

                # Rank Evaluation
                rank_eval = profile_cell.find(
                    'span', class_='club-profile-rank-eval')
                rank_eval_text = rank_eval.text.strip() if rank_eval else 'N/A'

                # Player Name
                name = profile_cell.find('span', class_='club-profile-name')
                name_text = name.text.strip() if name else 'N/A'

                # Friend ID
                fid = profile_cell.find('span', class_='club-profile-fid')
                fid_text = fid.text.strip() if fid else 'N/A'

                # ===== CELL 2: Fans =====
                fans_cell = cells[1]

                # Total Fans
                total_fans_span = fans_cell.find(
                    'span', class_='club-profile-cell-reg-span')
                total_fans = total_fans_span.text.strip() if total_fans_span else 'N/A'

                # Fan change (positive or negative)
                fan_change_span = fans_cell.find(
                    'span', class_=['club-profile-positive', 'club-profile-negative'])
                fan_change = fan_change_span.text.strip() if fan_change_span else '0'

                # ===== CELL 3: 30-day Daily Average =====
                avg_cell = cells[2]
                daily_avg_span = avg_cell.find(
                    'span', class_='club-profile-cell-reg-span')
                daily_avg = daily_avg_span.text.strip() if daily_avg_span else 'N/A'

                # ===== CELL 4: Last Login =====
                login_cell = cells[3]
                last_login_span = login_cell.find(
                    'span', class_='club-profile-cell-reg-span')
                last_login = last_login_span.text.strip() if last_login_span else 'N/A'

                # Assemble member object
                member = {
                    'rank': rank_eval_text,
                    'name': name_text,
                    'friend_id': fid_text,
                    'role': role,
                    'total_fans': total_fans,
                    'fan_change': fan_change,
                    'daily_avg': daily_avg,
                    'last_login': last_login
                }

                members.append(member)
                if i < 5:  # Only print first 5 to avoid spam
                    print(f"   ✓ {name_text} (ID: {fid_text}) - Role: {role}")

            except Exception as e:
                print(f"   ⚠️ Error parsing row {i}: {e}")
                continue

        if len(rows) > 5:
            print(f"   ... and {len(rows) - 5} more members")

        self.session_data['total_members'] = len(members)
        return members

    async def save_results(self, data):
        """Save results to JSON and CSV in output directory"""
        if not data or not data['members']:
            print("\n⚠️ No data to save")
            return

        # Save to JSON
        json_path = self.output_dir / 'club_members.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved to: {json_path}")

        # Save to CSV
        csv_path = self.output_dir / 'club_members.csv'
        df = pd.DataFrame(data['members'])
        df.to_csv(csv_path, index=False, encoding='utf-8')
        print(f"💾 Saved to: {csv_path}")

        # Print summary
        print(f"\n📊 Summary:")
        print(f"   Total members: {len(data['members'])}")
        print(
            f"   Leaders: {len([m for m in data['members'] if m['role'] == 'Leader'])}")
        print(
            f"   Officers: {len([m for m in data['members'] if m['role'] == 'Officer'])}")
        print(
            f"   Regular members: {len([m for m in data['members'] if m['role'] == 'Member'])}")

        # Sample output
        print(f"\n📋 Sample members (first 3):")
        for member in data['members'][:3]:
            print(f"\n   Name: {member['name']}")
            print(f"   ID: {member['friend_id']}")
            print(f"   Rank: {member['rank']}")
            print(f"   Role: {member['role']}")
            print(f"   Fans: {member['total_fans']} ({member['fan_change']})")
            print(f"   Daily Avg: {member['daily_avg']}")
            print(f"   Last Login: {member['last_login']}")

    async def close(self):
        """Close browser properly with cleanup"""
        try:
            if self.browser:
                await self.browser.stop()
                # Give browser time to clean up
                await asyncio.sleep(0.5)
                print("🛑 Browser closed")
        except Exception as e:
            # Suppress cleanup warnings - they're harmless
            print("🛑 Browser closed")

    async def scrape_club(self, circle_id='Uchoom'):
        """Main scraping method"""
        try:
            await self.initialize_browser()
            await self.create_session()

            url = f"https://chronogenesis.net/club_profile?circle_id={circle_id}"
            await self.navigate_to_page(url, max_wait=30)

            data = await self.extract_club_data()

            if data and data['success']:
                print(f"\n✅ SUCCESS! Extracted {len(data['members'])} members")
                await self.save_results(data)
            else:
                print("\n⚠️ No data extracted")
                print("   The page may still be loading.")
                print("   Try increasing wait times or check browser window")

            # Save session info
            session_path = self.output_dir / 'session_data.json'
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, indent=2)
            print(f"💾 Session data saved to {session_path}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await self.close()
