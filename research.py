import time
import asyncio
import logging
import lmstudio as lms
from .web_search import search_web

logger = logging.getLogger(__name__)

async def research_session(start_q: str, duration_min: int, channel):
    """
    Runs until duration_min elapses. Each round:
      1) announce + private thought
      2) safe web search
      3) safe summarization
      4) safe follow-up question
    """
    # Late import to share the SAME globals
    from .danzar import embedder, faiss_index, rag_texts, settings, save_rag

    start_ts  = time.time()
    end_ts    = start_ts + duration_min * 60
    current_q = start_q

    sys_p = settings["personality"] + (
        "\n\nYou are the RESEARCHER: before searching, think about why you’re asking this "
        "and what you expect to find."
    )

    round = 1
    while time.time() < end_ts:
        await channel.send(f"🔄 Research Round {round}: Question → “{current_q}”")

        # 1) private thought
        try:
            thought_msgs = [
                {"role":"system","content":sys_p},
                {"role":"user",  "content":f"Why research “{current_q}”? What am I looking for?"}
            ]
            tchat   = lms.Chat.from_history({"messages": thought_msgs})
            thought = lms.llm("gemma-3-12b-it").respond(tchat).content.strip()
            await channel.send(thought)
        except Exception as e:
            logger.exception(f"[round {round}] thought error")
            await channel.send(f"⚠️ Thought gen failed: {e}")

        # 2) web search
        web_ctx = ""
        try:
            web_ctx = search_web(current_q) or ""
            await channel.send(f"🔍 Web results:\n{web_ctx}")
            rag_texts.append(f"web: {web_ctx}")
            faiss_index.add(embedder.encode([web_ctx], convert_to_numpy=True))
        except Exception as e:
            logger.exception(f"[round {round}] web search error")
            await channel.send(f"⚠️ Web search failed: {e}")

        # 3) summarize
        summary = ""
        if web_ctx:
            try:
                sum_msgs = [
                    {"role":"system","content":sys_p},
                    {"role":"user",  "content":f"Summarize in 3 bullets:\n{web_ctx}"}
                ]
                schat   = lms.Chat.from_history({"messages": sum_msgs})
                summary = lms.llm("gemma-3-12b-it").respond(schat).content.strip()
                await channel.send(f"📄 Summary:\n{summary}")
                rag_texts.append(f"summary: {summary}")
                faiss_index.add(embedder.encode([summary], convert_to_numpy=True))
            except Exception as e:
                logger.exception(f"[round {round}] summary error")
                await channel.send(f"⚠️ Summarization failed: {e}")
        else:
            await channel.send("⚠️ Skipping summary—no web results.")

        # 4) next question
        next_q = current_q
        try:
            fq_msgs = [
                {"role":"system","content":sys_p},
                {"role":"user","content":(
                    f"Based on that summary, what should I research next about “{current_q}”? "
                    "Give me a one-sentence question."
                )}
            ]
            fqchat = lms.Chat.from_history({"messages": fq_msgs})
            next_q = lms.llm("gemma-3-12b-it").respond(fqchat).content.strip()
            await channel.send(f"➡️ Follow-up Question: {next_q}")
            rag_texts.append(f"follow_up: {next_q}")
            faiss_index.add(embedder.encode([next_q], convert_to_numpy=True))
        except Exception as e:
            logger.exception(f"[round {round}] follow-up error")
            await channel.send(f"⚠️ Follow-up question failed: {e}")

        current_q = next_q
        round += 1

        # time left
        rem = max(0, int(end_ts - time.time()))
        m, s = divmod(rem, 60)
        await channel.send(f"⏳ Time left: {m:02d}:{s:02d}")

        await asyncio.sleep(1)

    save_rag()
    await channel.send(f"✅ Research complete! Indexed {round-1} rounds.")
