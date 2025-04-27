#!/usr/bin/env python3
import os
from flask import Flask, request, jsonify

# ─── Override LlamaIndex defaults to use local HF embeddings ─────────────
from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Use all-MiniLM-L6-v2 locally (no OpenAI API key)
Settings.embed_model = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")

# ─── Now import & load your persisted index ───────────────────────────────
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.llms.lmstudio import LMStudio

# Point at your LM Studio local API & model
llm = LMStudio(
    model_name="Gemma 3 12B Instruct",  # exact name in your LM Studio UI
    host="http://localhost:8080",       # default LM Studio port
    temperature=0.7
)

# Load the index from disk (it was persisted under ./index_storage/)
storage_context = StorageContext.from_defaults(persist_dir="./index_storage")
index = load_index_from_storage(storage_context)

# Create a RAG‑capable query engine
query_engine = index.as_query_engine(llm=llm)

# ─── Flask app setup ──────────────────────────────────────────────────────
app = Flask(__name__)

@app.route("/query", methods=["POST"])
def query():
    """
    Expects JSON payload: { "q": "<user question>" }
    Returns JSON: {
      "answer": "<LLM-generated answer>",
      "docs": [ "<raw chunk 1>", "<raw chunk 2>", ... ]
    }
    """
    data = request.get_json(force=True)
    user_q = data.get("q", "").strip()
    if not user_q:
        return jsonify({"error": "No question provided"}), 400

    # 1) Run Retrieval + Generation
    response = query_engine.query(user_q)
    answer = str(response)

    # 2) Extract the raw source chunks used
    docs = []
    if hasattr(response, "source_nodes"):
        docs = [node.get_content() for node in response.source_nodes]

    return jsonify({
        "answer": answer,
        "docs": docs
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 RAG server running on http://0.0.0.0:{port}/query")
    app.run(host="0.0.0.0", port=port)
