from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import text


async def vector_retrieve(
    db: AsyncSession, cv_vector: list[float], job_ids: list[UUID], top_k: int = 100
):
    query = text("""
        WITH top_chunks AS (
            SELECT job_id, embedding <=> :cv_vector AS distance
            FROM job_chunks
            WHERE job_id = ANY(:job_ids)
            ORDER BY embedding <=> :cv_vector
            LIMIT :overfetch
        )
        SELECT job_id, MIN(distance) AS best_distance
        FROM top_chunks
        GROUP BY job_id
        ORDER BY best_distance
        LIMIT :top_k
    """)
    result = await db.execute(
        query,
        {
            "cv_vector": str(cv_vector),
            "job_ids": job_ids,
            "overfetch": top_k * 5,  # enough chunks survive to get top_k distinct jobs
            "top_k": top_k,
        },
    )
    return [(row.job_id, 1 - row.best_distance) for row in result.all()]


async def get_top_chunks_for_reranking(
    db: AsyncSession, cv_vector: list[float], job_ids: list[UUID], n_chunks: int = 3
):
    query = text("""
        SELECT jc.job_id, jc.chunk_text, jc.embedding <=> :cv_vector AS distance
        FROM job_chunks jc
        WHERE jc.job_id = ANY(:job_ids)
        ORDER BY jc.job_id, distance
    """)
    result = await db.execute(query, {"cv_vector": str(cv_vector), "job_ids": job_ids})
    chunks_by_job: dict[UUID, list[str]] = {}
    for row in result.all():
        chunks_by_job.setdefault(row.job_id, [])
        if len(chunks_by_job[row.job_id]) < n_chunks:
            chunks_by_job[row.job_id].append(row.chunk_text)
    return chunks_by_job
