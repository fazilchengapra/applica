from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tailoring.models import (
    STAGE_SEQUENCE,
    EvidenceItem,
    EvidenceMatrix,
    StrategyBrief,
    TailoringRun,
    TailoringRunStatus,
    TailoringStage,
)


async def get_or_create_run(
    session: AsyncSession, user_id: int, job_id: UUID, cv_version_id: UUID
) -> tuple[TailoringRun, bool]:
    """Fetch the run for this (user, job, cv_version), creating it if absent.

    A new cv_version_id always starts a fresh run rather than mutating an
    existing one — re-tailoring after a CV update is a distinct attempt.
    """
    result = await session.execute(
        select(TailoringRun).where(
            TailoringRun.user_id == user_id,
            TailoringRun.job_id == job_id,
            TailoringRun.cv_version_id == cv_version_id,
        )
    )
    run = result.scalar_one_or_none()
    if run is not None:
        return run, False

    run = TailoringRun(user_id=user_id, job_id=job_id, cv_version_id=cv_version_id)
    session.add(run)
    try:
        await session.flush()
    except IntegrityError:
        # Lost a race to create the same row — fetch the winner's row instead.
        await session.rollback()
        result = await session.execute(
            select(TailoringRun).where(
                TailoringRun.user_id == user_id,
                TailoringRun.job_id == job_id,
                TailoringRun.cv_version_id == cv_version_id,
            )
        )
        return result.scalar_one(), False
    return run, True


async def try_claim_stage(
    session: AsyncSession, run_id: UUID, stage: TailoringStage
) -> bool:
    """Atomically claim a stage: succeeds only if the row is currently at
    this exact stage and pending or previously failed (retry). A stage
    that's already 'processing' (another worker) or has moved past this
    stage (already done) is not claimable — caller should skip."""
    result = await session.execute(
        update(TailoringRun)
        .where(
            TailoringRun.id == run_id,
            TailoringRun.stage == stage,
            TailoringRun.status.in_(
                [TailoringRunStatus.pending, TailoringRunStatus.failed]
            ),
        )
        .values(status=TailoringRunStatus.processing, error_message=None)
    )
    return result.rowcount == 1


async def advance_stage(session: AsyncSession, run_id: UUID) -> None:
    """Move the run to the next stage on success. The final stage (critic)
    has no 'next' — it's marked completed in place instead."""
    result = await session.execute(
        select(TailoringRun.stage).where(TailoringRun.id == run_id)
    )
    current = result.scalar_one()
    idx = STAGE_SEQUENCE.index(current)

    if idx == len(STAGE_SEQUENCE) - 1:
        await session.execute(
            update(TailoringRun)
            .where(TailoringRun.id == run_id)
            .values(status=TailoringRunStatus.completed)
        )
        return

    next_stage = STAGE_SEQUENCE[idx + 1]
    await session.execute(
        update(TailoringRun)
        .where(TailoringRun.id == run_id)
        .values(stage=next_stage, status=TailoringRunStatus.pending)
    )


async def fail_run(session: AsyncSession, run_id: UUID, error_message: str) -> None:
    await session.execute(
        update(TailoringRun)
        .where(TailoringRun.id == run_id)
        .values(status=TailoringRunStatus.failed, error_message=error_message[:2000])
    )


async def save_evidence_matrix(
    session: AsyncSession, run_id: UUID, items: list[dict]
) -> None:
    matrix = EvidenceMatrix(tailoring_run_id=run_id)
    session.add(matrix)
    await session.flush()
    for item in items:
        session.add(
            EvidenceItem(
                evidence_matrix_id=matrix.id,
                requirement=item["requirement"],
                status=item["status"],
                confidence=item["confidence"],
                evidence_chunk_ids=item.get("evidence_chunk_ids"),
                excerpt=item.get("excerpt"),
                reasoning=item.get("reasoning"),
            )
        )


async def save_strategy_brief(session: AsyncSession, run_id: UUID, brief: dict) -> None:
    session.add(
        StrategyBrief(
            tailoring_run_id=run_id,
            tone=brief.get("tone"),
            section_order=brief.get("section_order"),
            lead_experiences=brief.get("lead_experiences"),
            gaps_to_address=brief.get("gaps_to_address"),
            keywords_to_weave=brief.get("keywords_to_weave"),
            reasoning=brief.get("reasoning"),
        )
    )


async def load_evidence_matrix(session: AsyncSession, run_id: UUID) -> dict | None:
    """Reconstruct the evidence_matrix dict shape from storage, for
    resuming a pipeline where evidence_match already succeeded."""
    result = await session.execute(
        select(EvidenceMatrix).where(EvidenceMatrix.tailoring_run_id == run_id)
    )
    matrix = result.scalar_one_or_none()
    if matrix is None:
        return None

    items_result = await session.execute(
        select(EvidenceItem).where(EvidenceItem.evidence_matrix_id == matrix.id)
    )
    return {
        "items": [
            {
                "requirement": item.requirement,
                "status": item.status,
                "confidence": float(item.confidence),
                "evidence_chunk_ids": item.evidence_chunk_ids,
                "excerpt": item.excerpt,
                "reasoning": item.reasoning,
            }
            for item in items_result.scalars().all()
        ]
    }
