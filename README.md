# 🐎 Chronogenesis Club Tracker Bot

A specialized Discord bot designed to track **Uma Musume** club statistics. It automates the process of fetching daily fan counts, tracking individual member performance against weekly targets, and generating rich visual reports for club management.

## ✨ Features

*   **Cloudflare Bypass:** Uses `nodriver` to navigate through Cloudflare protections indistinguishably from a real user.
*   **Daily Scheduling:** Automatically fetches data at a configured time (e.g., 08:00 AM JST/UTC+7).
*   **Performance Tracking:**
    *   Tracks daily fan gains (green numbers from the game).
    *   Visual indicators for members meeting the **3 Million/Week** quota.
    *   🔥 **Hot:** >1M/day | ✅ **Safe:** >430k/day | ⚠️ **Low:** <430k/day | 💤 **Inactive:** 0.
*   **Data Persistence:** Saves JSON history of every scrape for backup and potential future analysis.
*   **Manual Trigger:** Admin command `/scrape_now` for immediate updates.

---

## 🛠️ Technical Architecture: How it Works

This project is a hybrid application combining an asynchronous Discord bot with a stealth browser automation tool.

### 1. The Core Stack
*   **Language:** Python 3.10+
*   **Discord Interface:** `discord.py` (Asynchronous wrapper for Discord API).
*   **Browser Automation:** `nodriver` (A successor to undetected-chromedriver). It controls a real Chrome instance using the Chrome DevTools Protocol (CDP) to bypass anti-bot detection.
*   **Scheduling:** `APScheduler` (AsyncIO implementation) handles Cron-like timing without blocking the bot's heartbeat.

### 2. The Data Pipeline
When a scrape is triggered (either by Schedule or Command):

1.  **Acquisition (The Scraper):**
    *   The bot launches a Chromium browser instance.
    *   It navigates to `chronogenesis.net` and waits for specific JavaScript events (Cloudflare checks, Table rendering).
    *   It extracts the HTML content once the DOM is fully loaded.
2.  **Parsing (The Logic):**
    *   `BeautifulSoup4` parses the raw HTML.
    *   It locates specific table cells for **Total Fans** and **Daily Gain** (the green text).
3.  **Normalization (The Bridge):**
    *   Raw strings (e.g., `"+1,440,104"`) are cleaned and converted into Integers.
    *   Data is saved to `output/club_members.json` (Current State) and `history/` (Archival).
4.  **Visualization (The Bot):**
    *   The bot reads the processed JSON.
    *   It calculates if the daily gain meets the weekly quota (`3,000,000 / 7 ≈ 428,571`).
    *   It constructs a Discord Embed with status icons and sends it to the target channel.

---

## 🚀 Installation Guide

### Prerequisites
*   **Python 3.10** or higher.
*   **Google Chrome** installed on the machine running the bot.
*   **Git** (to clone this repo).

### Step 1: Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/ChronogenesisBot.git
cd ChronogenesisBot
```

### Step 2: Environment Setup
Create a virtual environment to keep dependencies clean:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

Install the required packages:
```bash
pip install -r requirements.txt
```

### Step 3: Configuration (.env)
Create a file named `.env` in the root directory. **Do not commit this file to GitHub.**
Copy and paste the following, filling in your details:

```ini
# --- SECRETS ---
DISCORD_TOKEN=your_long_bot_token_here

# --- DISCORD IDS ---
# Enable Developer Mode in Discord -> Right Click Server/Channel -> Copy ID
GUILD_ID=123456789012345678
CHANNEL_ID=987654321098765432

# --- CONFIGURATION ---
# Time to auto-scrape (24h format)
NOTIFICATION_TIME=08:00
# The specific club name/ID in the URL
SCRAPE_CLUB_NAME=Uchoom
```

### Step 4: Discord Permissions
1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Select your application -> **Bot**.
3.  **Enable Privileged Intents** (Toggle these ON):
    *   Server Members Intent
    *   Message Content Intent
4.  **Invite the Bot:** Go to OAuth2 -> URL Generator.
    *   Scopes: `bot`, `applications.commands`.
    *   Permissions: `Send Messages`, `Embed Links`, `View Channels`.
    *   Copy the URL and invite it to your server.

---

## 🎮 Usage

### Starting the Bot
Run the bot from your terminal:
```bash
python discord_bot.py
```
*You should see: `✅ Bot online as [BotName]`*

### Commands
Type these in your Discord server:

*   `/scrape_now` - **(Admin Only)** Forces an immediate scrape, updates the data, and posts the report.
*   **Automatic** - The bot will silently run every day at the time specified in `.env`.

---

## 📂 Project Structure

```text
ChronogenesisBot/
├── chronogenesis_scraper/   # The Core Scraper Module
│   ├── scraper.py           # Nodriver/Selenium Logic
│   └── main.py              # CLI entry point (optional)
├── output/                  # Stores the latest JSON/CSV data
├── history/                 # Archives daily JSON snapshots
├── discord_bot.py           # Main Discord Bot Application
├── scraper_integration.py   # Data processing bridge
├── config.py                # Configuration loader
└── .env                     # Secrets (Excluded from Git)
```

## ⚠️ Disclaimer
This bot utilizes browser automation to retrieve public data. It is intended for private club management. Please respect the rate limits and terms of service of the target website. The developer is not responsible for IP bans resulting from aggressive scraping settings.