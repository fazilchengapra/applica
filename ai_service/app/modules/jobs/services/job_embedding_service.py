from app.core.embedding_client import embeddings

async def embed_chunks(chunks: list[str]) -> list[list[float]]:

    if not chunks:
        return []
    return await embeddings.aembed_documents(chunks)
