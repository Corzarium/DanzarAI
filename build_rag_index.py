#!/usr/bin/env python3
from pathlib import Path
import sys
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, StorageContext, load_index_from_storage
from llama_index.llms.lmstudio import LMStudio
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

def main():
    # 1) Ensure your scraped text exists
    data_dir = Path("scraped_chunks")
    if not data_dir.exists():
        print("❌ scraped_chunks/ not found—run the scraper first.", file=sys.stderr)
        sys.exit(1)

    # 2) Configure LM Studio as your LLM
    Settings.llm = LMStudio(
        model_name="Gemma 3 12B Instruct",
        host="http://localhost:8080",
        max_tokens=512
    )

    # 3) Configure your local HuggingFace embedder
    hf_embed = HuggingFaceEmbedding(model_name="all-MiniLM-L6-v2")
    Settings.embed_model = hf_embed

    # 4) Load documents and build the index
    docs = SimpleDirectoryReader(str(data_dir)).load_data()
    index = VectorStoreIndex.from_documents(docs)

    # 5) Persist the index to disk
    persist_path = "./index_storage"
    index.storage_context.persist(persist_dir=persist_path)
    print(f"✅ Index persisted to: {persist_path}")

    # 6) (Optional) Demonstrate reload
    sc = StorageContext.from_defaults(persist_dir=persist_path)
    reloaded = load_index_from_storage(sc)
    print("✅ Reloaded index from storage; ready to query.")

if __name__ == "__main__":
    main()
