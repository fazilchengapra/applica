"""Vector similarity search over embedded RAG chunks (pgvector)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rag.models.chunk import Chunk


def build_chunk_search(
    embedding: list[float],
    top_k: int = 5,
    access_levels: list[str] | None = None,
):
    """Build the pgvector query: nearest ``top_k`` chunks to ``embedding``.

    ``cosine_distance`` binds the Python list through the ``vector`` type's
    bind processor (list -> text), and Postgres coercs it via the ``<=>``
    operator, so no explicit ``CAST`` is needed.
    """
    distance = Chunk.embedding.cosine_distance(embedding).label("distance")

    stmt = (
        select(Chunk, distance)
        .where(Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    )
    if access_levels:
        stmt = stmt.where(Chunk.access_level.in_(access_levels))
    return stmt


async def search_chunks(
    db: AsyncSession,
    *,
    embedding: list[float],
    top_k: int = 5,
    access_levels: list[str] | None = None,
) -> list[tuple[Chunk, float]]:
    """Execute the search; pairs each :class:`Chunk` with cosine similarity."""
    stmt = build_chunk_search(embedding, top_k, access_levels)
    rows = (await db.execute(stmt)).all()
    return [(row[0], 1.0 - float(row[1])) for row in rows]