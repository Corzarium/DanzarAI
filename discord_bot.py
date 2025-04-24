#!/usr/bin/env python3
"""
discord_bot.py — basic Discord bot that auto‑joins a voice channel.
"""

import os
import json
import logging
from dotenv import load_dotenv

import discord
from discord.ext import commands

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Load .env & Settings ───────────────────────────────────────────────────
load_dotenv()  # grabs DISCORD_TOKEN from .env

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{SETTINGS_FILE} not found! Create one with at least “auto_join_channel”.")
        return {}
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return {}

settings = load_settings()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if not DISCORD_TOKEN:
    raise RuntimeError("❌ DISCORD_TOKEN not set in your environment!")

# ─── Bot & Intents ───────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states    = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ─── Auto‑Join on Ready ───────────────────────────────────────────────────────
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")

    chan_id = settings.get("auto_join_channel")
    if not chan_id:
        logger.warning("No auto_join_channel in settings.json, skipping.")
        return

    try:
        vc = bot.get_channel(int(chan_id))
    except Exception:
        vc = None

    if isinstance(vc, discord.VoiceChannel):
        try:
            await vc.connect()
            logger.info(f"✅ Auto‑joined voice channel: {vc.name} ({vc.id})")
        except Exception as e:
            logger.error(f"❌ Failed to auto‑join voice channel: {e}")
    else:
        logger.warning(f"Couldn’t find a voice channel with ID {chan_id}. Check your settings.json.")

# ─── Example Command ─────────────────────────────────────────────────────────
@bot.command(name="ping")
async def ping(ctx):
    """Just to prove the bot is alive."""
    await ctx.send("🏓 Pong!")

# ─── Run the Bot ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
