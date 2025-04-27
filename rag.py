import requests

RAG_ENDPOINT = "http://localhost:5000/query"

def query_rag(question: str) -> str:
    try:
        resp = requests.post(RAG_ENDPOINT, json={"q": question})
        data = resp.json() if resp.status_code == 200 else {}
        return data.get("answer", "…")
    except Exception:
        return "I’m having trouble reaching the RAG server."
