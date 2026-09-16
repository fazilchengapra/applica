import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.tailoring.critic.helpers.fabrication_check import check_fabrication
from app.modules.tailoring.critic.helpers.quality_judge import judge_quality
from app.modules.tailoring.critic.schemas import CriticVerdict
from app.modules.tailoring.models import EvidenceItem, EvidenceMatrix


async def run_critic(
    db: AsyncSession,
    tailoring_run_id: uuid.UUID,
    cv_draft: dict,
    strategy: dict,
) -> CriticVerdict:
    """Read evidence and return a verdict; transaction ownership stays with caller."""
    result = await db.execute(
        select(EvidenceItem)
        .join(EvidenceMatrix, EvidenceItem.evidence_matrix_id == EvidenceMatrix.id)
        .where(EvidenceMatrix.tailoring_run_id == tailoring_run_id)
    )
    evidence_items = [
        {
            "id": str(item.id),
            "requirement": item.requirement,
            "status": item.status,
            "confidence": float(item.confidence),
            "evidence_chunk_ids": item.evidence_chunk_ids,
            "excerpt": item.excerpt,
            "reasoning": item.reasoning,
        }
        for item in result.scalars().all()
    ]
    flags = check_fabrication(cv_draft, evidence_items, strategy)
    high = [flag for flag in flags if flag.severity == "high"]
    if high:
        return CriticVerdict(
            approved=False,
            fabrication_flags=flags,
            quality_score=0.0,
            issues=[
                f"{flag.context}: {flag.reason} (claim: {flag.claim!r})"
                for flag in high
            ],
            reasoning="Fabrication check failed; quality review skipped.",
        )

    judgment = await judge_quality(cv_draft, strategy)
    return CriticVerdict(
        approved=judgment.quality_score >= settings.CRITIC_QUALITY_THRESHOLD,
        fabrication_flags=flags,
        quality_score=judgment.quality_score,
        issues=judgment.issues,
        reasoning="Quality review completed.",
    )
