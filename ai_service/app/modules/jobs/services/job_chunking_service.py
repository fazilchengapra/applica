from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.jobs.models import JobChunk
from app.modules.jobs.utils.chunking import chunk_text
from app.modules.jobs.services.job_embedding_service import embed_chunks

import logging

logger = logging.getLogger(__name__)


async def chunk_and_embed_job(
    session: AsyncSession,
    job_id,
    description: str,
) -> int:
    
    chunks = chunk_text(description)
    if not chunks:
        logger.warning(f"No chunks produced for job_id={job_id} (empty description?)")
        return 0

    try:
        embeddings = await embed_chunks(chunks)
    except Exception:
        logger.exception(f"Embedding failed for job_id={job_id}")
        return 0

    if len(embeddings) != len(chunks):
        logger.error(
            f"Embedding count mismatch for job_id={job_id}: "
            f"{len(chunks)} chunks vs {len(embeddings)} embeddings"
        )
        return 0

    rows = [
        {
            "job_id": job_id,
            "chunk_index": idx,
            "content": chunk,
            "embedding": embedding,
        }
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]

    stmt = (
        pg_insert(JobChunk)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["job_id", "chunk_index"])
    )
    await session.execute(stmt)
    await session.commit()

    return len(rows)