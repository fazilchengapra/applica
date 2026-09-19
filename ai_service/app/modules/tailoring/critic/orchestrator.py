"""Critic orchestration: pure-LLM review of the writer's CV draft."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.tailoring.critic.helpers.quality_judge import judge_quality
from app.modules.tailoring.critic.schemas import CriticVerdict
from app.modules.tailoring.models import EvidenceItem, EvidenceMatrix


async def run_critic(
    db: AsyncSession,
    tailoring_run_id: uuid.UUID,
    cv_draft: dict,
    strategy: dict,
) -> CriticVerdict:
    """Load evidence context and let the LLM critic review the draft."""
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

    judgment = await judge_quality(cv_draft, strategy, evidence_items=evidence_items)
    return CriticVerdict(
        approved=judgment.quality_score >= settings.CRITIC_QUALITY_THRESHOLD,
        fabrication_flags=[],
        quality_score=judgment.quality_score,
        issues=judgment.issues,
        reasoning="Quality review completed.",
    )