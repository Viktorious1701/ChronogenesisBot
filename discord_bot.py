import discord
from discord.ext import commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import logging
import sys
from datetime import datetime

from config import *
from scraper_integration import ChrononesisClubScraperBot

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('discord_bot')

# Bot Setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)
scheduler = AsyncIOScheduler()
scraper_bot = ChrononesisClubScraperBot(output_dir=OUTPUT_DIR)
scrape_lock = asyncio.Lock()

# --- CLUB RULES ---
WEEKLY_REQ = 3_000_000
DAILY_REQ = WEEKLY_REQ / 7  # 428,571 fans


@bot.event
async def on_ready():
    logger.info(f'✅ Bot online as {bot.user}')
    if not scheduler.running:
        h, m = map(int, NOTIFICATION_TIME.split(':'))
        scheduler.add_job(daily_routine, CronTrigger(
            hour=h, minute=m, timezone=TIMEZONE), id='daily_scrape')
        scheduler.start()
    await bot.tree.sync()


async def daily_routine():
    await run_and_notify()


async def run_and_notify(interaction=None):
    if scrape_lock.locked():
        msg = "⚠️ Scraper is busy."
        if interaction:
            await interaction.followup.send(msg)
        return

    # Run the Scraper
    async with scrape_lock:
        data = await scraper_bot.run_scrape(CLUB_NAME)

    if not data:
        msg = "❌ Scrape failed."
        if interaction:
            await interaction.followup.send(msg)
        return

    # Sort by Daily Gain (Highest to Lowest)
    data.sort(key=lambda x: x['gain'], reverse=True)

    # Calculate Totals
    total_gain = sum(d['gain'] for d in data)

    # Create Embed
    embed = discord.Embed(
        title=f"📊 Daily Check: {CLUB_NAME}",
        description=f"**Target:** {int(DAILY_REQ):,}/day (3M/week)",
        timestamp=datetime.now(),
        color=discord.Color.from_rgb(46, 204, 113)  # Green
    )

    embed.add_field(
        name="Club Total",
        value=f"📈 **+{total_gain:,}** fans today",
        inline=False
    )

    # Generate Member List with Status Icons
    desc_text = ""
    for i, m in enumerate(data, 1):
        gain = m['gain']

        # --- ICON LOGIC ---
        if gain >= 1_000_000:
            icon = "🔥"  # Carrying the club
        elif gain >= DAILY_REQ:
            icon = "✅"  # Safe (Met 430k)
        elif gain > 0:
            icon = "⚠️"  # Falling behind (< 430k)
        else:
            icon = "💤"  # Slacking (0 gain)

        # Line format: #01 ⚠️ Name (+Gain)
        line = f"`#{i:02}` {icon} **{m['name']}**: +{gain:,}\n"

        # Discord Embed Field Limit is 1024 chars
        if len(desc_text) + len(line) > 1000:
            embed.add_field(name="Member Performance",
                            value=desc_text, inline=False)
            desc_text = line
        else:
            desc_text += line

    if desc_text:
        embed.add_field(name="Member Performance",
                        value=desc_text, inline=False)

    embed.set_footer(text="🔥=1M+ | ✅=On Track | ⚠️=Behind Pace | 💤=Zero")

    # Send Message
    if interaction:
        await interaction.followup.send(embed=embed)
    else:
        for guild_id, channel_id in NOTIFICATION_CHANNELS.items():
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)


@bot.tree.command(name="scrape_now", description="Force update")
async def scrape_now(interaction: discord.Interaction):
    await interaction.response.defer()
    await run_and_notify(interaction)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
