from app.core.embedding_client import embeddings

async def embed_cv_text(raw_text: str) -> list[float]:
    return await embeddings.aembed_query(raw_text)      # input_type="query" under the hood

# batch (for chunks)
# vectors = await embeddings.aembed_documents(chunk_texts)  input_type="document" under the hood