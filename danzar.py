#!/usr/bin/env python3
import os
import re
import json
import threading
import asyncio
import logging
import subprocess
import atexit

from dotenv import load_dotenv
load_dotenv()

import discord
from discord.ext import commands, tasks

import lmstudio as lms
from Danzar.gui import run_gui

# ─── BLIP for image captioning ─────────────────────────────────────────────
from transformers import BlipProcessor, BlipForConditionalGeneration
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model     = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# OCR
import pytesseract
from pytesseract import TesseractNotFoundError
from PIL import Image

# RAG / embeddings
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Web search
from Danzar.web_search import search_web

# Vision search & captioning
from Danzar.vision_search import reverse_image_search, caption_image

# TTS
from TTS.api import TTS
from pydub import AudioSegment

# ─── Logging & Settings ────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
HISTORY_FILE  = os.path.join(os.path.dirname(__file__), "rag_histories.json")

def load_settings():
    defaults = {
        "voice": "p231",
        "volume": 4,
        "personality": (
            "You are Danzar, an elemental mage known for your sharp wit "
            "and occasional sarcasm.\nWrap private reasoning in <think>…</think>."
        ),
        "auto_join_channel": None
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                defaults.update(json.load(f))
        except Exception as e:
            logger.warning(f"Could not load settings: {e}")
    return defaults

def save_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    logger.info("Settings saved.")

settings = load_settings()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") or ""
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN not set in your environment")

# ─── Build the FAISS index for RAG over conversation ───────────────────────
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
            else:
                logger.info(f"{HISTORY_FILE} empty or invalid, starting fresh RAG")
        except Exception as e:
            logger.error(f"Failed to load RAG histories: {e}")

atexit.register(save_rag)
load_rag()

# ─── Discord Bot Setup ──────────────────────────────────────────────────────
intents       = discord.Intents.default()
intents.message_content = True
intents.voice_states    = True

bot          = commands.Bot(command_prefix="!", intents=intents)
request_queue = asyncio.Queue()

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    bot.loop.create_task(_process_queue())
    chan = settings.get("auto_join_channel")
    if chan:
        try:
            vc = bot.get_channel(int(chan)) or await bot.fetch_channel(int(chan))
            if isinstance(vc, discord.VoiceChannel):
                await vc.connect()
                logger.info(f"✅ Auto-joined voice channel: {vc.name}")
        except Exception as e:
            logger.error(f"Auto-join failed: {e}")

@bot.event
async def on_disconnect():
    logger.warning("⚠️ Disconnected from Discord gateway! Attempting reconnect…")

@bot.event
async def on_resumed():
    logger.info("✅ Reconnected to Discord gateway.")

@tasks.loop(seconds=60)
async def keep_alive():
    _ = bot.latency
    logger.debug(f"Heartbeat ping (latency {bot.latency:.3f}s)")

@keep_alive.before_loop
async def before_keep_alive():
    await bot.wait_until_ready()

keep_alive.start()

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id == bot.user.id and before.channel and after.channel is None:
        logger.warning(f"🔄 Voice dropped from '{before.channel.name}', reconnecting…")
        try:
            await before.channel.connect()
            logger.info(f"✅ Re-joined '{before.channel.name}'")
        except Exception as e:
            logger.error(f"❌ Failed to re-join: {e}")

@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    if re.search(rf"(?i)(<@!?{bot.user.id}>|danzar\b)", msg.content):
        if msg.attachments:
            os.makedirs("downloads", exist_ok=True)
            for att in msg.attachments:
                if att.content_type and att.content_type.startswith("image/"):
                    p = os.path.join("downloads", att.filename)
                    await att.save(p)
                    await request_queue.put((msg.author, p, msg.channel))
        txt = re.sub(rf"(?i)(<@!?{bot.user.id}>|danzar\b)", "", msg.content).strip()
        if txt:
            await request_queue.put((msg.author, txt, msg.channel))
        return
    await bot.process_commands(msg)

# ─── Text-to-Speech Setup ───────────────────────────────────────────────────
coqui = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False, gpu=False)
def synthesize(text, fn="ai.wav"):
    coqui.tts_to_file(text=text, speaker=settings["voice"], file_path=fn)
    return fn

def play_audio(path):
    seg = AudioSegment.from_file(path)
    tmp = "tmp.wav"
    seg.export(tmp, format="wav")
    subprocess.run(["ffplay","-nodisp","-autoexit",tmp],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try: os.remove(tmp)
    except: pass

def clean_md(txt):
    txt = re.sub(r"\*\*(.*?)\*\*", r"\1", txt)
    return re.sub(r"\*(.*?)\*\*", r"\1", txt)

# ─── Main Processing + RAG Loop ────────────────────────────────────────────
async def _process_queue():
    while True:
        author, query, channel = await request_queue.get()

        # 1) Embed user query
        emb_u = embedder.encode(query, convert_to_numpy=True)
        if emb_u.ndim == 1: emb_u = emb_u.reshape(1, -1)
        faiss_index.add(emb_u)
        rag_texts.append(f"user: {query}")

        # 2) OCR vs text
        if os.path.isfile(query):
            try:
                img = Image.open(query).convert("RGB")
                extracted = pytesseract.image_to_string(img, config="--psm 6").strip()
            except TesseractNotFoundError:
                logger.warning("⚠️ Tesseract not found, skipping OCR.")
                extracted = ""
            finally:
                os.remove(query)
            user_content = extracted or ""
        else:
            user_content = query

        # 3) RAG retrieval of past convo
        if len(rag_texts) > 1:
            D, I = faiss_index.search(emb_u, k=min(3, len(rag_texts)))
            relevant = [rag_texts[i] for i in I[0] if i < len(rag_texts)]
            rag_ctx = "\n".join(relevant)
        else:
            rag_ctx = ""

        # 4) Build system prompt
        sys_prompt = settings["personality"]
        if rag_ctx:
            sys_prompt += "\n\nRelevant past conversation:\n" + rag_ctx

        # 5) Decide branch
        if os.path.isfile(query) and user_content:
            # image caption + OCR branch
            caption = caption_image(query)
            msgs = [
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": f"Image Caption:\n{caption}\nOCR Text:\n{user_content}"}
            ]
            chat = lms.Chat.from_history({"messages": msgs})
            full_reply = lms.llm("gemma-3-12b-it").respond(chat).content.strip()

        elif re.search(r"\b(hi|hello|hey)\b", query, re.I):
            full_reply = "Hey there! 😊"

        else:
            # plain text or vision-search could be triggered via teach/research
            msgs = [
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": query}
            ]
            chat = lms.Chat.from_history({"messages": msgs})
            full_reply = lms.llm("gemma-3-12b-it").respond(chat).content.strip()

        # 6) Embed assistant reply
        emb_a = embedder.encode(full_reply, convert_to_numpy=True)
        if emb_a.ndim == 1: emb_a = emb_a.reshape(1, -1)
        faiss_index.add(emb_a)
        rag_texts.append(f"assistant: {full_reply}")

        # 7) Send + TTS
        placeholder = await channel.send(f"{author.display_name} Thinking...")
        cleaned    = re.sub(r"<think>.*?</think>", "", full_reply, flags=re.DOTALL).strip()
        wav        = synthesize(cleaned)
        threading.Thread(target=play_audio, args=(wav,), daemon=True).start()
        await placeholder.edit(content=f"💬 {author.display_name}: {cleaned}")

        request_queue.task_done()

# ─── Entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=lambda: bot.run(DISCORD_TOKEN, reconnect=True),
                     daemon=True).start()
    run_gui(bot, request_queue, settings, save_settings)
