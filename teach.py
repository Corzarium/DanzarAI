# Danzar/teach.py

import time
import logging
import numpy as np
import lmstudio as lms
import os

from .web_search import search_web
from .danzar import embedder, faiss_index, rag_texts, save_rag

logger = logging.getLogger(__name__)

async def teaching_session(start_q: str, turns: int, channel):
    """
    Self-supervised teach loop (rounds):
      1. Ask question.
      2. Search web.
      3. Summarize.
      4. Generate follow-up question.
      5. Repeat.
    """
    question = start_q.strip()
    for i in range(1, turns+1):
        await channel.send(f"❓ Round {i}: {question}")
        # index question
        emb_q = embedder.encode(question, convert_to_numpy=True)
        emb_q = emb_q.reshape(1,-1) if emb_q.ndim==1 else emb_q
        faiss_index.add(emb_q); rag_texts.append(f"user: {question}")

        # web search
        try:
            snippets = search_web(question)
            await channel.send(f"🔍 Snippets:\n{snippets}")
        except Exception as e:
            snippets = f"[search failed: {e}]"; await channel.send(f"⚠️ {e}")

        # index snippets
        emb_r = embedder.encode(snippets, convert_to_numpy=True)
        emb_r = emb_r.reshape(1,-1) if emb_r.ndim==1 else emb_r
        faiss_index.add(emb_r); rag_texts.append(f"search: {snippets}")

        # summarize
        sum_p = (
            "You are Danzar, summarizing research. Output bullet points ONLY.\n"
            f"Snippets:\n{snippets}\nSummary:"
        )
        chat_s = lms.Chat.from_history({"messages":[{"role":"system","content":sum_p}]})
        summary = lms.llm("gemma-3-12b-it").respond(chat_s).content.strip()
        await channel.send(f"📝 Summary:\n{summary}")

        emb_s = embedder.encode(summary, convert_to_numpy=True)
        emb_s = emb_s.reshape(1,-1) if emb_s.ndim==1 else emb_s
        faiss_index.add(emb_s); rag_texts.append(f"assistant: {summary}")

        # next question
        q_p = (
            "You are Danzar. From the summary, output EXACTLY ONE follow-up question ending with '?' only.\n"
            f"Summary:\n{summary}\nNext question:"
        )
        chat_q = lms.Chat.from_history({"messages":[{"role":"system","content":q_p}]})
        next_q = lms.llm("gemma-3-12b-it").respond(chat_q).content.strip()
        if not next_q.endswith("?"):
            lines = [ln for ln in next_q.splitlines() if ln.strip().endswith("?")]
            next_q = lines[-1].strip() if lines else question
        await channel.send(f"➡️ Next: {next_q}")

        emb_q2 = embedder.encode(next_q, convert_to_numpy=True)
        emb_q2 = emb_q2.reshape(1,-1) if emb_q2.ndim==1 else emb_q2
        faiss_index.add(emb_q2); rag_texts.append(f"user: {next_q}")

        question = next_q

    save_rag()
    await channel.send(f"✅ Teaching complete: {turns} rounds.")

async def research_session(topic: str, minutes: int, channel):
    """
    Vision+text timer-based research:
      • Caption image or search text.
      • Reverse-image search if image.
      • Summarize + next question.
      • Loop until time expires.
    """
    end_time = time.time() + minutes*60
    question = topic.strip()
    round_n = 1

    from .vision_search import reverse_image_search, caption_image

    while time.time() < end_time:
        await channel.send(f"🔎 Research Round {round_n}: {question}")

        # index question
        emb_q = embedder.encode(question, convert_to_numpy=True)
        emb_q = emb_q.reshape(1,-1) if emb_q.ndim==1 else emb_q
        faiss_index.add(emb_q); rag_texts.append(f"user: {question}")

        # vision vs text
        if os.path.isfile(question):
            # caption
            caption = caption_image(question)
            await channel.send(f"🖼️ Caption: {caption}")
            emb_c = embedder.encode(caption, convert_to_numpy=True).reshape(1,-1)
            faiss_index.add(emb_c); rag_texts.append(f"caption: {caption}")

            # reverse-image search
            try:
                vis = reverse_image_search(question)
                await channel.send(f"🌐 Vision results:\n{vis}")
                vis_text = "\n".join([r['link'] for r in vis])
            except Exception as e:
                vis_text = f"[vision search failed: {e}]"
                await channel.send(f"⚠️ {e}")

            emb_v = embedder.encode(vis_text, convert_to_numpy=True).reshape(1,-1)
            faiss_index.add(emb_v); rag_texts.append(f"vision: {vis_text}")

            # use caption as next query
            question = caption
        else:
            # text search
            try:
                snippets = search_web(question)
                await channel.send(f"📑 Snippets:\n{snippets}")
            except Exception as e:
                snippets = f"[search failed: {e}]"; await channel.send(f"⚠️ {e}")

            emb_r = embedder.encode(snippets, convert_to_numpy=True)
            emb_r = emb_r.reshape(1,-1) if emb_r.ndim==1 else emb_r
            faiss_index.add(emb_r); rag_texts.append(f"search: {snippets}")

            # pose next
            follow_p = (
                "You are Danzar. From the snippets, ask ONE follow-up question ending with '?'."
            )
            chat_f = lms.Chat.from_history({
                "messages":[
                    {"role":"system","content":follow_p},
                    {"role":"assistant","content":snippets}
                ]
            })
            question = lms.llm("gemma-3-12b-it").respond(chat_f).content.strip()
            if not question.endswith("?"):
                lines=[ln for ln in question.splitlines() if ln.strip().endswith("?")]
                question = lines[-1].strip() if lines else topic

        await channel.send(f"➡️ Next: {question}")

        emb_q2 = embedder.encode(question, convert_to_numpy=True)
        emb_q2 = emb_q2.reshape(1,-1) if emb_q2.ndim==1 else emb_q2
        faiss_index.add(emb_q2); rag_texts.append(f"user: {question}")

        round_n += 1

    save_rag()
    await channel.send(f"✅ Research complete: {minutes} minutes.")
