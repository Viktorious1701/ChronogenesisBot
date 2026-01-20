import discord
from discord.ext import commands
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
import logging
import sys
from datetime import datetime, timedelta

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
DAILY_REQ = WEEKLY_REQ / 7


@bot.event
async def on_ready():
    logger.info(f'✅ Bot online as {bot.user}')
    if not scheduler.running:
        h, m = map(int, NOTIFICATION_TIME.split(':'))
        scheduler.add_job(daily_routine, CronTrigger(
            hour=h, minute=m, timezone=TIMEZONE), id='daily_scrape')
        scheduler.start()

    try:
        synced = await bot.tree.sync()
        logger.info(f"🔄 Synced {len(synced)} commands.")
    except Exception as e:
        logger.error(f"❌ Failed to sync commands: {e}")


async def daily_routine():
    await run_and_notify()


async def run_and_notify(interaction=None):
    if scrape_lock.locked():
        msg = "⚠️ Scraper is busy."
        if interaction:
            await interaction.followup.send(msg)
        return

    async with scrape_lock:
        data = await scraper_bot.run_scrape(CLUB_NAME)

    if not data:
        msg = "❌ Scrape failed."
        if interaction:
            await interaction.followup.send(msg)
        return

    data.sort(key=lambda x: x['gain'], reverse=True)
    total_gain = sum(d['gain'] for d in data)

    embed = discord.Embed(
        title=f"📊 Daily Check: {CLUB_NAME}",
        description=f"**Target:** {int(DAILY_REQ):,}/day (3M/week)",
        timestamp=datetime.now(),
        color=discord.Color.green()
    )
    embed.add_field(name="Club Total",
                    value=f"📈 **+{total_gain:,}** fans today", inline=False)

    desc_text = ""
    for i, m in enumerate(data, 1):
        gain = m['gain']
        if gain >= 1_000_000:
            icon = "🔥"
        elif gain >= DAILY_REQ:
            icon = "✅"
        elif gain > 0:
            icon = "⚠️"
        else:
            icon = "💤"

        line = f"`#{i:02}` {icon} **{m['name']}**: +{gain:,}\n"
        if len(desc_text) + len(line) > 1000:
            embed.add_field(name="Member Performance",
                            value=desc_text, inline=False)
            desc_text = line
        else:
            desc_text += line

    if desc_text:
        embed.add_field(name="Member Performance",
                        value=desc_text, inline=False)

    if interaction:
        await interaction.followup.send(embed=embed)
    else:
        for guild_id, channel_id in NOTIFICATION_CHANNELS.items():
            channel = bot.get_channel(channel_id)
            if channel:
                await channel.send(embed=embed)

# ==================== COMMANDS ====================


@bot.tree.command(name="scrape_now", description="Force update (Admin)")
async def scrape_now(interaction: discord.Interaction):
    # Optional Security Check
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("⛔ Admin only.", ephemeral=True)
        return
    await interaction.response.defer()
    await run_and_notify(interaction)


@bot.tree.command(name="leaderboard", description="Show rankings over time")
@app_commands.choices(period=[
    app_commands.Choice(name="📅 Current Month", value="monthly"),
    app_commands.Choice(name="📅 Current Week", value="weekly"),
])
async def leaderboard(interaction: discord.Interaction, period: app_commands.Choice[str]):
    await interaction.response.defer()
    now = datetime.now()
    if period.value == "monthly":
        start_date = now.replace(
            day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = (now - timedelta(days=now.weekday())
                      ).replace(hour=0, minute=0, second=0, microsecond=0)

    rankings = scraper_bot.db.get_leaderboard(start_date.isoformat())

    if not rankings:
        await interaction.followup.send("⚠️ No history data found yet.")
        return

    embed = discord.Embed(title=f"🏆 {period.name}", color=discord.Color.gold())
    desc_text = ""
    for i, m in enumerate(rankings, 1):
        line = f"`#{i}` **{m['current_name']}**: +{m['period_gain']:,}\n"
        if len(desc_text) + len(line) > 1000:
            embed.add_field(name="Rankings", value=desc_text, inline=False)
            desc_text = line
        else:
            desc_text += line
    if desc_text:
        embed.add_field(name="Rankings", value=desc_text, inline=False)

    await interaction.followup.send(embed=embed)

# --- NEW ADMIN COMMAND ---


@bot.tree.command(name="member_lookup", description="Admin: Check lifetime stats for a specific member")
@app_commands.describe(name="Partial name of the member")
async def member_lookup(interaction: discord.Interaction, name: str):
    # 🔒 AUTHORIZATION CHECK 🔒
    # Only users with the 'Administrator' role permission can pass this block.
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer()

    # Query Database
    stats = scraper_bot.db.lookup_member(name)

    if not stats:
        await interaction.followup.send(f"❌ Could not find member matching '**{name}**'.")
        return

    # Format Dates
    try:
        f_date = datetime.fromisoformat(
            stats['first_seen']).strftime('%Y-%m-%d')
        l_date = datetime.fromisoformat(
            stats['last_seen']).strftime('%Y-%m-%d')
    except:
        f_date = str(stats['first_seen'])[:10]
        l_date = str(stats['last_seen'])[:10]

    embed = discord.Embed(
        title=f"👤 Member File: {stats['name']}", color=discord.Color.dark_teal())
    embed.add_field(name="🆔 ID", value=stats['id'], inline=True)
    embed.add_field(name="📅 Tracked Since", value=f_date, inline=True)
    embed.add_field(name="📉 Original Fans",
                    value=f"{stats['original_fans']:,}", inline=True)
    embed.add_field(name="📈 Current Fans",
                    value=f"{stats['current_fans']:,}", inline=True)
    embed.add_field(name="💰 Lifetime Accumulation",
                    value=f"**+{stats['accumulated_fans']:,}**", inline=False)
    embed.set_footer(text=f"Data range: {f_date} to {l_date}")

    await interaction.followup.send(embed=embed)

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN missing in .env")
    else:
        bot.run(DISCORD_TOKEN)
