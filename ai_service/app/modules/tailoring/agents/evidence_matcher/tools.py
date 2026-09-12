"""Read-only evidence tools for the CV tailoring evidence matcher.

CVs are currently persisted as a single ``MasterCVVersion.raw_text`` value, not
as a ``cv_chunks`` table. ``search_cv_chunks`` therefore creates stable,
deterministic excerpts from that persisted text at query time. Its chunk IDs
always include the source CV-version UUID so an agent's citation remains
traceable to an actual database record.
"""

from __future__ import annotations
import re
from collections.abc import Iterable
from typing import Any
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

# These tools run from Celery workers.  A pooled asyncpg connection created in
# Celery's parent process cannot safely be reused after the worker forks, so
# use the worker-safe NullPool session provider.
from app.db.celery_db import get_celery_db_session as get_session_context
from app.modules.jobs.models import Job, JobSkill, Skill
from app.modules.jobs.utils.chunking import chunk_text
from app.modules.master_cv.models import CVSkill
from app.modules.matching.repositories.profile_repository import (
    get_current_completed_cv,
)

MAX_TOP_K = 10
_WORD_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-/]*", re.IGNORECASE)


def _query_terms(text: str) -> set[str]:
    """Return comparable terms without turning punctuation-only input into evidence."""
    return {term.lower() for term in _WORD_RE.findall(text) if len(term) > 1}


def _rank_chunks(query: str, chunks: Iterable[str]) -> list[tuple[int, str, float]]:
    """Rank CV excerpts by explicit term overlap.

    This deliberately returns no result for a query with no explicit overlap:
    evidence matching must favour a false negative over an unsupported claim.
    """
    query_terms = _query_terms(query)
    if not query_terms:
        return []

    ranked: list[tuple[int, str, float]] = []
    for index, chunk in enumerate(chunks):
        chunk_terms = _query_terms(chunk)
        overlap = query_terms & chunk_terms
        if not overlap:
            continue

        # Recall is the useful signal here: a short requirement should not be
        # penalised merely because the CV excerpt contains more context.
        score = len(overlap) / len(query_terms)
        ranked.append((index, chunk, round(score, 4)))

    return sorted(ranked, key=lambda item: item[2], reverse=True)


async def _cv_skills(cv_id: UUID) -> list[dict[str, str]]:
    async with get_session_context() as session:
        result = await session.execute(
            select(Skill.name, Skill.normalized_name)
            .join(CVSkill, CVSkill.skill_id == Skill.id)
            .where(CVSkill.cv_id == cv_id)
            .order_by(Skill.normalized_name)
        )
        return [
            {
                "name": row.name,
                "normalized_name": row.normalized_name,
            }
            for row in result.all()
        ]


@tool
async def search_cv_chunks(
    query: str, user_id: int, top_k: int = 5
) -> list[dict[str, Any]]:
    """Find grounded CV excerpts supporting a requirement.

    Each returned ``chunk_id`` is a deterministic ``<cv_version_uuid>:<index>``
    citation. Only use returned excerpts as evidence.
    """
    limit = max(1, min(top_k, MAX_TOP_K))

    async with get_session_context() as session:
        cv = await get_current_completed_cv(session, user_id)
        if cv is None or not cv.raw_text:
            return []

        ranked = _rank_chunks(query, chunk_text(cv.raw_text))[:limit]
        return [
            {
                "chunk_id": f"{cv.id}:{index}",
                "cv_version_id": str(cv.id),
                "content": content,
                "match_score": score,
            }
            for index, content, score in ranked
        ]


@tool
async def get_cv_metadata(user_id: int) -> dict[str, Any]:
    """Fetch the current completed CV's structured metadata and extracted skills."""
    async with get_session_context() as session:
        cv = await get_current_completed_cv(session, user_id)
        if cv is None:
            return {
                "found": False,
                "error": "No completed current CV found for this user.",
            }

        cv_id = cv.id
        target_role = cv.target_role
        parsed_data = cv.parsed_data or {}
        raw_text = cv.raw_text

    return {
        "found": True,
        "cv_version_id": str(cv_id),
        "target_role": target_role,
        "parsed_data": parsed_data,
        "skills": await _cv_skills(cv_id),
        "raw_text": raw_text
    }


@tool
async def get_job_requirement_detail(job_id: str) -> dict[str, Any]:
    """Fetch a job's description and its extracted required/preferred skills.

    The current schema has no separate job-requirements table, so ``job_id`` is
    the job UUID and ``requirements`` is built from persisted ``job_skills``.
    """
    try:
        parsed_job_id = UUID(job_id)
    except ValueError:
        return {"found": False, "error": "job_id must be a valid UUID."}

    async with get_session_context() as session:
        job = await session.get(Job, parsed_job_id)
        if job is None:
            return {"found": False, "error": "Job not found."}

        result = await session.execute(
            select(Skill.name, Skill.normalized_name, JobSkill.skill_type)
            .join(JobSkill, JobSkill.skill_id == Skill.id)
            .where(JobSkill.job_id == parsed_job_id)
            .order_by(JobSkill.skill_type, Skill.normalized_name)
        )
        requirements = [
            {
                "name": row.name,
                "normalized_name": row.normalized_name,
                "requirement_type": row.skill_type,
            }
            for row in result.all()
        ]

    return {
        "found": True,
        "job_id": str(job.id),
        "title": job.title,
        "description": job.description,
        "requirements": requirements,
    }


TOOLS = [search_cv_chunks, get_cv_metadata, get_job_requirement_detail]
