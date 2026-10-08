"""Assemble retrieved chunks into a prompt-ready context block."""

from app.modules.rag.models.chunk import Chunk
from app.modules.rag.repositories.vector import search_chunks


def build_context(chunks: list[Chunk]) -> str:
    """Render the top chunks as a single text block for generation.

    Each chunk is prefixed with its source (doc type, access level, chunk
    index) so a future answer generator can ground and cite its response.
    """
    return "\n\n".join(_render(chunk) for chunk in chunks)


def _render(chunk: Chunk) -> str:
    header = f"[{chunk.doc_type} | access={chunk.access_level} | #{chunk.chunk_index}]"
    return f"{header}\n{chunk.content}"


async def retrieve(
    db,
    *,
    query_embedding: list[float],
    top_k: int = 5,
    access_levels: list[str] | None = None,
) -> tuple[list[Chunk], str]:
    """Search for the nearest chunks and return them with a built context."""
    results = await search_chunks(
        db,
        embedding=query_embedding,
        top_k=top_k,
        access_levels=access_levels,
    )
    chunks = [chunk for chunk, _score in results]
    return chunks, build_context(chunks)