from app.core.config import settings
from langchain_voyageai import VoyageAIEmbeddings

embeddings = VoyageAIEmbeddings(
    model="voyage-3.5",
    voyage_api_key=settings.VOYAGE_API_KEY,
    output_dimension=1024,
)
