import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from transformers import pipeline

# ─── CONFIG ────────────────────────────────────────────────────────────────────
MAX_RESULTS   = 5      # how many DuckDuckGo links
CHUNK_SIZE    = 1000   # chars per chunk
CHUNK_OVERLAP = 200    # chars overlap
TOP_K         = 4      # how many chunks to retrieve
# Summarizer (runs on GPU if you set device=0)
SUMMARIZER = pipeline(
    "summarization",
    model="facebook/bart-large-cnn",
    device=0  # set to 0 for cuda:0, or -1 to force CPU
)
# Embedder (runs on GPU if you set device="cuda:0")
EMBEDDER = SentenceTransformer(
    "all-MiniLM-L6-v2",
    device="cuda:0"
)
EMBED_DIM = EMBEDDER.get_sentence_embedding_dimension()
# ────────────────────────────────────────────────────────────────────────────────

def web_search(query: str, max_results: int = MAX_RESULTS) -> list[str]:
    """Use DDGS to fetch top DuckDuckGo results."""
    with DDGS() as ddgs:
        results = ddgs.text(query, max_results=max_results)
    return [r["href"] for r in results if r.get("href")]

def fetch_and_clean(url: str) -> str:
    """Download & strip out scripts/styles/etc., return plain text."""
    try:
        r = requests.get(url, timeout=5)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "aside"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines)
    except Exception:
        return ""

def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split a long string into overlapping chunks."""
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks

def build_faiss_index(chunks: list[str]):
    """Embed chunks and store in a cosine-sim FAISS index."""
    embs = EMBEDDER.encode(chunks, show_progress_bar=False)
    embs = embs / np.linalg.norm(embs, axis=1, keepdims=True)
    index = faiss.IndexFlatIP(EMBED_DIM)
    index.add(embs)
    return index

def research_topic_free(topic: str) -> str:
    """
    1) DuckDuckGo search (DDGS)
    2) Scrape & chunk
    3) Build FAISS + retrieve topK
    4) Summarize locally
    """
    print(f"🔍 Searching for “{topic}”…")
    urls = web_search(topic)
    docs = []
    for u in urls:
        txt = fetch_and_clean(u)
        if len(txt) > 300:
            docs.extend(chunk_text(txt))
    if not docs:
        return f"❌ No usable text found for “{topic}.”"

    print(f"📚 Embedding {len(docs)} chunks…")
    index = build_faiss_index(docs)

    q_emb = EMBEDDER.encode([topic])
    q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)
    D, I = index.search(q_emb, TOP_K)
    top_chunks = [docs[i] for i in I[0]]

    print(f"✂️ Summarizing top {TOP_K} chunks…")
    joined = "\n\n".join(top_chunks)
    if len(joined) > 3000:
        parts = chunk_text(joined, size=3000, overlap=500)
        summ = [
            SUMMARIZER(p, max_length=200, min_length=50, do_sample=False)[0]["summary_text"]
            for p in parts
        ]
        final = SUMMARIZER(
            " ".join(summ),
            max_length=200, min_length=50, do_sample=False
        )[0]["summary_text"]
    else:
        final = SUMMARIZER(
            joined,
            max_length=300, min_length=75, do_sample=False
        )[0]["summary_text"]

    return final
