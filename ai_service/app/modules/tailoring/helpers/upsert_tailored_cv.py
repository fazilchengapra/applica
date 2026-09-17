from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tailoring.models import StructuredCVDraft, TailoredCV, TailoredCVStatus


async def get_cv_draft(session: AsyncSession, run_id: UUID) -> StructuredCVDraft | None:
    """Full draft row — needed by the critic task for cv_template_id, not just cv_structure."""
    stmt = select(StructuredCVDraft).where(StructuredCVDraft.tailoring_run_id == run_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_tailored_cv(
    session: AsyncSession,
    *,
    run_id: UUID,
    cv_structure: dict[str, Any],
    critic_verdict: dict[str, Any],
    status: TailoredCVStatus,
) -> TailoredCV:
    """
    Persist the terminal outcome of a tailoring run — approved or failed-out
    after exhausting writer retries. Upserts by tailoring_run_id so a stray
    re-run of the critic task never creates a duplicate row.
    """
    stmt = (
        insert(TailoredCV)
        .values(
            tailoring_run_id=run_id,
            cv_structure=cv_structure,
            status=status,
            critic_score=critic_verdict.get("score"),
            critic_verdict=critic_verdict,
        )
        .on_conflict_do_update(
            index_elements=[TailoredCV.tailoring_run_id],
            set_={
                "cv_structure": cv_structure,
                "status": status,
                "critic_score": critic_verdict.get("score"),
                "critic_verdict": critic_verdict,
            },
        )
        .returning(TailoredCV)
    )
    result = await session.execute(stmt)
    return result.scalar_one()
