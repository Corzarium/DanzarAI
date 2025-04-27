#!/usr/bin/env python3
import argparse
import json
import re
from research_tool_free import research_topic_free
from transformers import pipeline

def self_teach(topic: str, max_iters: int = 3):
    """
    1) research topic → summary
    2) prompt LLM for JSON array of 3 follow-up subtopics
    3) parse JSON (fallback to regex)
    4) repeat on the first subtopic
    """
    llm = pipeline(
        "text2text-generation",
        model="google/flan-t5-base",  # or your local LLM
        device=0,
        max_new_tokens=128,
        num_beams=4,
        do_sample=False
    )

    memory = []
    current = topic
    for i in range(max_iters):
        print(f"\n🔍 Iteration {i+1}/{max_iters}: researching “{current}”…")
        summary = research_topic_free(current)
        memory.append((current, summary))

        prompt = (
            f"You just read this summary of **{current}**:\n\n"
            f"{summary}\n\n"
            "Now output exactly three *specific* follow-up sub-topics or research questions "
            "as a JSON array of strings, e.g.:\n"
            "[\"character classes and skill trees\",\"endgame monolith mechanics\",\"item crafting strategies\"]\n"
            "Do NOT include any other text."
        )
        out = llm(prompt)[0]["generated_text"].strip()
        print(f"\n🤖 Raw LLM output:\n{out}\n")

        # Try JSON parsing
        try:
            subs = json.loads(out)
            if not (isinstance(subs, list) and len(subs) >= 1):
                raise ValueError()
        except Exception:
            # fallback to regex
            subs = re.findall(r'^\s*\d*\.*\s*"?([^"\]\[]+)"?\s*$', out, flags=re.MULTILINE)

        if not subs:
            print("▶️ No valid sub-topics found—stopping early.")
            break

        next_topic = subs[0].strip()
        print(f"▶️ Next up: “{next_topic}”")
        current = next_topic

    return memory

def main():
    p = argparse.ArgumentParser(
        description="🔎 Free RAG research → local summarization (+ self-teaching)"
    )
    p.add_argument("topic", nargs="+", help="What do you want to research?")
    p.add_argument(
        "--iters", "-n", type=int, default=3,
        help="How many follow-up rounds to run"
    )
    args = p.parse_args()
    subject = " ".join(args.topic)

    print(f"\n🎓 Starting self-learning research on “{subject}” for up to {args.iters} rounds.\n")
    notes = self_teach(subject, max_iters=args.iters)

    for topic, summary in notes:
        print(f"\n--- {topic.upper()} ---\n{summary}\n")

if __name__ == "__main__":
    main()
