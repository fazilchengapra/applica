from app.core.config import settings
from langchain_voyageai import VoyageAIEmbeddings

embeddings = VoyageAIEmbeddings(
    model="voyage-3.5",
    voyage_api_key=settings.VOYAGE_API_KEY,
    output_dimension=1024,
)

async def embed_cv_text(raw_text: str) -> list[float]:
    return await embeddings.aembed_query(raw_text)      # input_type="query" under the hood

# batch (for chunks)
# vectors = await embeddings.aembed_documents(chunk_texts)  input_type="document" under the hood