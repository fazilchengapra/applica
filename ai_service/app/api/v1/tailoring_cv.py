"""HTTP API for tailored CVs and on-demand template rendering."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.cv_render.tasks import render_tailored_cv_task
from app.modules.cv_template.repository import get_by_id as get_active_template
from app.modules.tailoring.models import CVRenderStatus, TailoredCV, TailoringRun
from app.modules.tailoring.schemas import (
    RenderCVAccepted,
    RenderCVRequest,
    TailoredCVOut,
)
from app.shared.utils.s3 import get_public_url

router = APIRouter(prefix="/tailored-cvs", tags=["Tailored CVs"])


async def _get_owned_tailored_cv(
    db: AsyncSession, tailored_cv_id: UUID, user_id: int
) -> TailoredCV:
    result = await db.execute(
        select(TailoredCV)
        .join(TailoringRun, TailoringRun.id == TailoredCV.tailoring_run_id)
        .where(
            TailoredCV.id == tailored_cv_id,
            TailoringRun.user_id == user_id,
        )
    )
    tailored_cv = result.scalar_one_or_none()
    if tailored_cv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tailored CV not found"
        )
    return tailored_cv


@router.get("/{tailored_cv_id}", response_model=TailoredCVOut)
async def get_tailored_cv(
    tailored_cv_id: UUID,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    tailored_cv = await _get_owned_tailored_cv(db, tailored_cv_id, user_id)
    return TailoredCVOut(
        id=tailored_cv.id,
        status=tailored_cv.status,
        render_status=tailored_cv.render_status,
        template_id=tailored_cv.cv_template_id,
        critic_score=tailored_cv.critic_score,
        file_url=(
            get_public_url(tailored_cv.file_s3_key) if tailored_cv.file_s3_key else None
        ),
        created_at=tailored_cv.created_at,
    )


@router.post(
    "/{tailored_cv_id}/render",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RenderCVAccepted,
)
async def render_tailored_cv(
    tailored_cv_id: UUID,
    body: RenderCVRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    tailored_cv = await _get_owned_tailored_cv(db, tailored_cv_id, user_id)
    template = await get_active_template(db, body.template_id)
    if template is None or not template.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Template is not available",
        )

    result = await db.execute(
        update(TailoredCV)
        .where(
            TailoredCV.id == tailored_cv.id,
            TailoredCV.render_status != CVRenderStatus.processing,
        )
        .values(
            cv_template_id=body.template_id,
            render_status=CVRenderStatus.processing,
            render_error_message=None,
        )
        .returning(TailoredCV.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tailored CV is already being rendered",
        )
    await db.commit()

    render_tailored_cv_task.delay(str(tailored_cv.id))
    return RenderCVAccepted(id=tailored_cv.id, render_status=CVRenderStatus.processing)
