from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.tools import tool

from app.modules.tailoring.agents.cv_writer.schemas import (
    StrategyBriefDTO, EvidenceItemDTO, CVChunkDTO, JobDTO, CVTemplateDTO, CVDraftDTO,
)
from ...models import (
    StrategyBrief, EvidenceMatrix, EvidenceItem, CVChunk, Job, CVTemplate, CVDraft,
)


# ---- Deterministic helpers (called directly by the orchestrator, not the LLM) ----

async def get_strategy_brief(db: AsyncSession, tailoring_run_id: UUID) -> StrategyBriefDTO:
    row = (
        await db.execute(
            select(StrategyBrief).where(StrategyBrief.tailoring_run_id == tailoring_run_id)
        )
    ).scalar_one()
    return StrategyBriefDTO.model_validate(row, from_attributes=True)


async def get_evidence_items(db: AsyncSession, tailoring_run_id: UUID) -> list[EvidenceItemDTO]:
    # two-hop: tailoring_run_id -> evidence_matrix.id -> evidence_items
    matrix_id = (
        await db.execute(
            select(EvidenceMatrix.id).where(EvidenceMatrix.tailoring_run_id == tailoring_run_id)
        )
    ).scalar_one()
    rows = (
        await db.execute(select(EvidenceItem).where(EvidenceItem.evidence_matrix_id == matrix_id))
    ).scalars().all()
    return [EvidenceItemDTO.model_validate(r, from_attributes=True) for r in rows]


async def resolve_evidence_chunks(db: AsyncSession, chunk_ids: list[UUID]) -> dict[UUID, CVChunkDTO]:
    if not chunk_ids:
        return {}
    rows = (
        await db.execute(select(CVChunk).where(CVChunk.id.in_(chunk_ids)))
    ).scalars().all()
    return {r.id: CVChunkDTO.model_validate(r, from_attributes=True) for r in rows}


async def get_job(db: AsyncSession, job_id: UUID) -> JobDTO:
    row = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one()
    return JobDTO.model_validate(row, from_attributes=True)


async def get_template(db: AsyncSession, template_id: UUID) -> CVTemplateDTO:
    row = (await db.execute(select(CVTemplate).where(CVTemplate.id == template_id))).scalar_one()
    return CVTemplateDTO.model_validate(row, from_attributes=True)


async def save_cv_draft(
    db: AsyncSession, tailoring_run_id: UUID, cv_template_id: UUID, tex_content: str
) -> CVDraftDTO:
    row = CVDraft(
        tailoring_run_id=tailoring_run_id,
        cv_template_id=cv_template_id,
        tex_content=tex_content,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return CVDraftDTO.model_validate(row, from_attributes=True)


# ---- LLM-bound tool (the "limited tool" the writer can call mid-generation) ----
# Only exposed if the model needs more chunk detail than what's already inlined
# in the prompt (e.g. it references a chunk_id it wasn't given full text for).

def make_resolve_chunk_tool(db: AsyncSession, chunk_pool: dict[UUID, CVChunkDTO]):
    @tool
    async def resolve_chunk(chunk_id: str) -> str:
        """Fetch full text for a CV evidence chunk by its id, when the excerpt
        already provided isn't enough detail to write from."""
        cid = UUID(chunk_id)
        if cid in chunk_pool:
            return chunk_pool[cid].content
        resolved = await resolve_evidence_chunks(db, [cid])
        return resolved[cid].content if cid in resolved else "Chunk not found."

    return resolve_chunk