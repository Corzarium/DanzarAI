#!/usr/bin/env python3
import os
import re
import json
import threading
import asyncio
import logging
import atexit
from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands
import lmstudio as lms

# Local modules
from gui import GUIChannel
from web_search import search_web
from vision_search import reverse_image_search, caption_image

# BLIP for captions
from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model     = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# OCR
import pytesseract
from pytesseract import TesseractNotFoundError

# RAG / embeddings
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# TTS
from tts import make_wav, play_wav

# ─── RAG State ─────────────────────────────────────────────────────────────
BASE = os.path.dirname(__file__)
SETTINGS_FILE = os.path.join(BASE, "settings.json")
HISTORY_FILE  = os.path.join(BASE, "rag_histories.json")

embedder    = SentenceTransformer('all-MiniLM-L6-v2')
dim         = embedder.get_sentence_embedding_dimension()
rag_texts   = []
faiss_index = faiss.IndexFlatL2(dim)

def save_rag():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(rag_texts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Could not save RAG histories: {e}")

def load_rag():
    global rag_texts, faiss_index
    rag_texts   = []
    faiss_index = faiss.IndexFlatL2(dim)
    if os.path.exists(HISTORY_FILE):
        try:
            raw = json.load(open(HISTORY_FILE, "r", encoding="utf-8"))
            if isinstance(raw, list) and raw:
                rag_texts = raw
                emb = embedder.encode(rag_texts, convert_to_numpy=True)
                if emb.ndim == 1:
                    emb = emb.reshape(1, -1)
                faiss_index.add(emb)
        except Exception as e:
            logger.error(f"Failed to load RAG histories: {e}")

atexit.register(save_rag)
load_rag()

# ─── Settings & Logging ────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_settings():
    defaults = {
        "voice": "p231",
        "volume": 4,
        "personality": (
            "You are Danzar, an elemental mage with sharp wit. "
            "Wrap private reasoning in <think>…</think>."
        ),
        "auto_join_channel": None
    }
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            defaults.update(json.load(f))
    except:
        pass
    return defaults

def save_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    logger.info("Settings saved.")

settings       = load_settings()
DISCORD_TOKEN  = os.getenv("DISCORD_TOKEN") or ""
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set")

SCREENSHOT_PATH = os.path.join(BASE, "gui_screenshot.png")

# ─── Discord Bot Setup ──────────────────────────────────────────────────────
intents                 = discord.Intents.default()
intents.message_content = True
intents.voice_states    = True

bot = commands.Bot(command_prefix="!", intents=intents)
request_queue = asyncio.Queue()

# ─── Context Buffer ─────────────────────────────────────────────────────────
MAX_HISTORY    = 6
chat_histories = {}  # channel_id -> history list
root_topics    = {}  # channel_id -> root query

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    bot.loop.create_task(_process_queue())
    chan = settings.get("auto_join_channel")
    if chan:
        try:
            vc = bot.get_channel(int(chan)) or await bot.fetch_channel(int(chan))
            if isinstance(vc, discord.VoiceChannel):
                await vc.connect()
        except Exception as e:
            logger.error(f"Auto-join failed: {e}")

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return

    mention_pattern = rf"(?i)(<@!?{bot.user.id}>|danzar\b)"
    if re.search(mention_pattern, msg.content):
        text = re.sub(mention_pattern, "", msg.content).strip()
        cid  = msg.channel.id
        if cid not in root_topics and text:
            root_topics[cid] = text

        # Handle image attachments
        if msg.attachments:
            os.makedirs("downloads", exist_ok=True)
            for att in msg.attachments:
                if att.content_type and att.content_type.startswith("image/"):
                    path = os.path.join("downloads", att.filename)
                    await att.save(path)
                    caption = caption_image(path)
                    await msg.channel.send(f"I’ve analyzed your screenshot. **{caption}**")
                    await request_queue.put((msg.author, path, msg.channel))
        if text:
            await request_queue.put((msg.author, text, msg.channel))
        return

    await bot.process_commands(msg)

async def _process_queue():
    while True:
        author, query, channel = await request_queue.get()
        cid = getattr(channel, "id", None)

        # ─── IMAGE branch ────────────────────────────────────────────────
        if isinstance(query, str) and os.path.isfile(query):
            try:
                # OCR
                img_obj   = Image.open(query).convert("RGB")
                extracted = pytesseract.image_to_string(img_obj, config="--psm 6").strip()
            except TesseractNotFoundError:
                extracted = ""
            except Exception as e:
                extracted = ""
                logger.warning(f"OCR error: {e}")

            # Caption (before any deletion)
            try:
                caption = caption_image(query)
            except Exception as e:
                caption = f"[Caption error: {e}]"

            # Only delete if not the GUI screenshot
            if os.path.abspath(query) != os.path.abspath(SCREENSHOT_PATH):
                try:
                    os.remove(query)
                except:
                    pass

            msgs = [
                {"role":"system", "content": settings["personality"]},
                {"role":"user",   "content": f"Image Caption:\n{caption}\nOCR Text:\n{extracted}"}
            ]
            chat = lms.Chat.from_history({"messages": msgs})
            reply = lms.llm("gemma-3-12b-it").respond(chat).content.strip()

        # ─── TEXT branch ─────────────────────────────────────────────────
        else:
            # small-talk bypass
            if isinstance(query, str) and re.match(r"^(hi|hello|hey|how are you)\b", query, re.I):
                canned = {
                    "hi":    "Hey there! How can I help today?",
                    "hello": "Hello! What would you like to talk about?",
                    "hey":   "Hey! What’s on your mind?"
                }
                reply = canned.get(query.lower().split()[0], "Hi! What can I do for you?")
                placeholder = await channel.send(f"{author.display_name} Thinking…")
                await placeholder.edit(content=reply)
                request_queue.task_done()
                continue

            hist = chat_histories.setdefault(cid, [])
            root = root_topics.get(cid, query)
            sys_txt = settings["personality"] + f"\n\nStay on topic: '{root}'."
            messages = [{"role":"system","content": sys_txt}]
            messages += hist[-MAX_HISTORY:]
            messages.append({"role":"user", "content": query})

            chat  = lms.Chat.from_history({"messages": messages})
            reply = lms.llm("gemma-3-12b-it").respond(chat).content.strip()

            # update history
            hist.append({"role":"user",      "content": query})
            hist.append({"role":"assistant", "content": reply})
            if len(hist) > 2*MAX_HISTORY:
                hist.pop(0); hist.pop(0)

        # ─── Respond + TTS (preserve <think> for GUI) ────────────────────
        placeholder = await channel.send(f"{author.display_name} Thinking…")

        # strip for TTS only
        tts_text = re.sub(r"<think>.*?</think>", "", reply, flags=re.DOTALL)
        tts_text = re.sub(r"https?://\S+", "", tts_text).strip()
        wav = make_wav(tts_text)
        threading.Thread(target=play_wav, args=(wav,), daemon=True).start()

        # GUIChannel gets raw reply so its DummyMessage can split out <think>
        if isinstance(channel, GUIChannel):
            await placeholder.edit(content=reply)
        else:
            await placeholder.edit(content=f"{author.display_name}: {tts_text}")

        request_queue.task_done()

if __name__ == "__main__":
    threading.Thread(
        target=lambda: bot.run(DISCORD_TOKEN, reconnect=True),
        daemon=True
    ).start()
    from gui import run_gui
    run_gui(bot, request_queue, settings, save_settings)
