from duckduckgo_search import DDGS

def search_web(query: str) -> str:
    snippets = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            body = r.get("body","").replace("\n"," ")
            snippets.append(f"- {body}")
    context = "\n".join(snippets)
    return f"I found these on the web:\n{context}"
