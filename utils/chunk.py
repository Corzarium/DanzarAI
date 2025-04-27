def chunk_text(text: str, max_chars: int=800) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    for p in paras:
        if len(p) <= max_chars:
            chunks.append(p)
        else:
            start = 0
            while start < len(p):
                end = min(len(p), start + max_chars)
                space = p.rfind(" ", start, end)
                if space > start: end = space
                chunks.append(p[start:end].strip())
                start = end
    return chunks
