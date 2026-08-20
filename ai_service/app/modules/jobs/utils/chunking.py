def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:

    if not text or not text.strip():
        return []

    words = text.split()
    total_words = len(words)

    if total_words <= chunk_size:
        return [text.strip()]

    chunks = []
    start = 0
    step = chunk_size - overlap

    if step <= 0:
        raise ValueError("overlap must be smaller than chunk_size")

    while start < total_words:
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))

        if end >= total_words:
            break

        start += step

    return chunks
