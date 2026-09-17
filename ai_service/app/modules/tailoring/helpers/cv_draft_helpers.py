import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.tailoring.models import CVDraft


async def upsert_cv_draft(
    session: AsyncSession,
    *,
    tailoring_run_id: uuid.UUID,
    cv_template_id: uuid.UUID,
    cv_structure: dict,
) -> CVDraft:
    stmt = (
        insert(CVDraft)
        .values(
            tailoring_run_id=tailoring_run_id,
            cv_template_id=cv_template_id,
            cv_structure=cv_structure,
        )
        .on_conflict_do_update(
            index_elements=[CVDraft.tailoring_run_id],
            set_={
                "cv_template_id": cv_template_id,
                "cv_structure": cv_structure,
                "updated_at": func.now(),
            },
        )
        .returning(CVDraft)
    )
    result = await session.execute(stmt)
    return result.scalar_one()
