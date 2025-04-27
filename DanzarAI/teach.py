# teach.py

import time
import os
import logging

import lmstudio as lms
import numpy as np

from web_search import search_web
import danzar
from vision_search import reverse_image_search, caption_image

# Pull in RAG state from danzar.py
embedder    = danzar.embedder
faiss_index = danzar.faiss_index
rag_texts   = danzar.rag_texts
save_rag    = danzar.save_rag

# Prepare logs
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
LOG_DIR      = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
TEACH_LOG    = os.path.join(LOG_DIR, "teach.log")
RESEARCH_LOG = os.path.join(LOG_DIR, "research.log")
open(TEACH_LOG,    "w", encoding="utf-8").close()
open(RESEARCH_LOG, "w", encoding="utf-8").close()

# Loggers
teach_logger = logging.getLogger("teach")
teach_logger.setLevel(logging.INFO)
h1 = logging.FileHandler(TEACH_LOG, encoding="utf-8")
h1.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
teach_logger.addHandler(h1)
teach_logger.propagate = False
teach_logger.info(f"--- Teach logger at {TEACH_LOG} ---")

research_logger = logging.getLogger("research")
research_logger.setLevel(logging.INFO)
h2 = logging.FileHandler(RESEARCH_LOG, encoding="utf-8")
h2.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
research_logger.addHandler(h2)
research_logger.propagate = False
research_logger.info(f"--- Research logger at {RESEARCH_LOG} ---")


# ─── Teaching Session ──────────────────────────────────────────────────────
async def teaching_session(start_q: str, turns: int, channel):
    root_topic = start_q.strip()
    question   = root_topic

    for i in range(1, turns + 1):
        teach_logger.info(f"ROUND {i} USER: {question}")
        await channel.send(f"**User:** {question}")

        try:
            snippets = search_web(question)
        except Exception as e:
            snippets = f"[search failed: {e}]"
        teach_logger.info(f"ROUND {i} SNIPPETS: {snippets}")
        await channel.send(f"**Danzar (snippets):**\n{snippets}")

        # index
        emb1 = embedder.encode(snippets, convert_to_numpy=True)
        if emb1.ndim == 1: emb1 = emb1.reshape(1,-1)
        faiss_index.add(emb1)
        rag_texts.append(f"search: {snippets}")

        sum_sys = "You are Danzar summarizing research. Bullet points ONLY."
        chat_s  = lms.Chat.from_history({
            "messages":[
                {"role":"system","content": sum_sys},
                {"role":"user",  "content": snippets}
            ]
        })
        summary = lms.llm("gemma-3-12b-it").respond(chat_s).content.strip()
        teach_logger.info(f"ROUND {i} SUMMARY: {summary}")
        await channel.send(f"**Danzar (summary):**\n{summary}")

        emb2 = embedder.encode(summary, convert_to_numpy=True)
        if emb2.ndim == 1: emb2 = emb2.reshape(1,-1)
        faiss_index.add(emb2)
        rag_texts.append(f"assistant: {summary}")

        nxt_sys = (
            f"You are Danzar. Root topic is '{root_topic}'. "
            "Using ONLY the summary below, output EXACTLY ONE strictly on-topic follow-up question ending with '?'"
        )
        chat_q  = lms.Chat.from_history({
            "messages":[
                {"role":"system","content": nxt_sys},
                {"role":"user",  "content": summary}
            ]
        })
        next_q = lms.llm("gemma-3-12b-it").respond(chat_q).content.strip()
        if not next_q.endswith("?"):
            lines = [ln for ln in next_q.splitlines() if ln.strip().endswith("?")]
            next_q = lines[-1].strip() if lines else question

        teach_logger.info(f"ROUND {i} NEXT QUESTION: {next_q}")
        await channel.send(f"**Danzar (next question):** {next_q}")

        remaining = turns - i
        if hasattr(channel, "teach_left_var"):
            channel.teach_left_var.set(f"Rounds left: {remaining}")

        question = next_q
        save_rag()

    teach_logger.info(f"Teaching complete: {turns} rounds")
    await channel.send(f"✅ Teaching complete: {turns} rounds.")


# ─── Research Session ──────────────────────────────────────────────────────
async def research_session(topic: str, minutes: int, channel):
    root_topic = topic.strip()
    question   = root_topic
    end_time   = time.time() + minutes*60
    rnd        = 1

    while time.time() < end_time:
        research_logger.info(f"ROUND {rnd} USER: {question}")
        await channel.send(f"**User:** {question}")

        if os.path.isfile(question):
            caption = caption_image(question)
            research_logger.info(f"ROUND {rnd} CAPTION: {caption}")
            await channel.send(f"**Caption:** {caption}")
            try:
                vis = reverse_image_search(question)
                vis_text = "\n".join(r["link"] for r in vis)
            except Exception as e:
                vis_text = f"[vision failed: {e}]"
            research_logger.info(f"ROUND {rnd} VISION: {vis_text}")
            await channel.send(f"**Vision:**\n{vis_text}")
            raw_ctx = caption + "\n" + vis_text
        else:
            try:
                snippets = search_web(question)
            except Exception as e:
                snippets = f"[search failed: {e}]"
            research_logger.info(f"ROUND {rnd} SNIPPETS: {snippets}")
            await channel.send(f"**Snippets:**\n{snippets}")
            raw_ctx = snippets

        embc = embedder.encode(raw_ctx, convert_to_numpy=True)
        if embc.ndim == 1: embc = embc.reshape(1,-1)
        faiss_index.add(embc)
        rag_texts.append(f"context: {raw_ctx}")

        sum_sys = "You are Danzar summarizing research. Bullet points ONLY."
        chat_s  = lms.Chat.from_history({
            "messages":[
                {"role":"system","content": sum_sys},
                {"role":"user",  "content": raw_ctx}
            ]
        })
        summary = lms.llm("gemma-3-12b-it").respond(chat_s).content.strip()
        research_logger.info(f"ROUND {rnd} SUMMARY: {summary}")
        await channel.send(f"**Summary:**\n{summary}")

        embs = embedder.encode(summary, convert_to_numpy=True)
        if embs.ndim == 1: embs = embs.reshape(1,-1)
        faiss_index.add(embs)
        rag_texts.append(f"assistant: {summary}")

        nxt_sys = (
            f"You are Danzar. Root topic is '{root_topic}'. "
            "Using ONLY the summary below, ask ONE strictly on-topic follow-up question ending with '?'"
        )
        chat_q = lms.Chat.from_history({
            "messages":[
                {"role":"system","content": nxt_sys},
                {"role":"user",  "content": summary}
            ]
        })
        next_q = lms.llm("gemma-3-12b-it").respond(chat_q).content.strip()
        if not next_q.endswith("?"):
            lines = [ln for ln in next_q.splitlines() if ln.strip().endswith("?")]
            next_q = lines[-1].strip() if lines else question

        research_logger.info(f"ROUND {rnd} NEXT Q: {next_q}")
        await channel.send(f"**Danzar (next question):** {next_q}")

        question = next_q
        rnd += 1
        save_rag()

    research_logger.info(f"Research complete: {minutes}m")
    await channel.send(f"✅ Research complete: {minutes} minutes.")
