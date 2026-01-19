"""
Main entry point for Chronogenesis Club Scraper
"""

import asyncio
from scraper import ChrononesisClubScraper


async def main():
    """Run the club scraper"""
    print("=" * 70)
    print("CHRONOGENESIS CLUB SCRAPER - v1.0")
    print("=" * 70)
    # ... (rest of your original code)
    scraper = ChrononesisClubScraper(output_dir='output')
    await scraper.scrape_club('Uchoom')
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
