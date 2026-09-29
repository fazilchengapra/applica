"""HTTP API for tailored CVs and on-demand template rendering."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.cv_render.tasks import render_tailored_cv_task
from app.modules.cv_template.repository import get_by_id as get_active_template
from app.modules.matching.models.job_match import JobMatch
from app.modules.matching.repositories.profile_repository import (
    get_current_completed_cv,
)
from app.modules.tailoring.helpers.run_helpers import get_or_create_run
from app.modules.tailoring.models import (
    CVRenderStatus,
    TailoredCV,
    TailoredCVStatus,
    TailoringRun,
)
from app.modules.tailoring.repository import list_tailored_cvs
from app.modules.tailoring.schemas import (
    CreateTailoredCVAccepted,
    CreateTailoredCVRequest,
    RenderCVAccepted,
    RenderCVRequest,
    TailoredCVJobOut,
    TailoredCVListItem,
    TailoredCVListOut,
    TailoredCVOut,
    TailoredCVTemplateOut,
    TailoringRunOut,
)
from app.modules.tailoring.tasks import evidence_match_task
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


def _to_list_item(row) -> TailoredCVListItem:
    template = None
    if row.template_id is not None:
        template = TailoredCVTemplateOut(
            id=row.template_id,
            title=row.template_title,
            image_url=(
                get_public_url(row.template_image_s3_key)
                if row.template_image_s3_key
                else None
            ),
        )

    job = None
    if row.job_id is not None:
        job = TailoredCVJobOut(
            id=row.job_id,
            title=row.job_title,
            company_name=row.company_display_name or row.company_normalized_name,
        )

    return TailoredCVListItem(
        id=row.id,
        created_at=row.created_at,
        status=row.cv_status,
        render_status=row.cv_render_status,
        render_error_message=row.render_error_message,
        critic_score=row.critic_score,
        critic_verdict=row.critic_verdict,
        file_url=get_public_url(row.file_s3_key) if row.file_s3_key else None,
        template=template,
        run=TailoringRunOut(
            id=row.run_id,
            stage=row.run_stage,
            status=row.run_status,
            error_message=row.run_error_message,
            critic_retry_count=row.critic_retry_count,
            job=job,
        ),
    )


@router.get("", response_model=TailoredCVListOut)
async def list_tailored_cvs_for_user(
    status_filter: TailoredCVStatus | None = Query(None, alias="status"),
    render_status_filter: CVRenderStatus | None = Query(None, alias="render_status"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    total, rows = await list_tailored_cvs(
        db,
        user_id,
        status_filter=status_filter,
        render_status_filter=render_status_filter,
        limit=limit,
        offset=offset,
    )
    return TailoredCVListOut(total=total, items=[_to_list_item(row) for row in rows])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=CreateTailoredCVAccepted,
    responses={
        404: {"description": "Match not found for this user"},
        409: {"description": "No completed master CV to tailor"},
    },
)
async def create_tailored_cv(
    body: CreateTailoredCVRequest,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    match = await db.scalar(
        select(JobMatch).where(
            JobMatch.id == body.match_id, JobMatch.user_id == user_id
        )
    )
    if match is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job match not found"
        )

    cv_version = await get_current_completed_cv(db, user_id)
    if cv_version is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No completed master CV to tailor",
        )

    template_id = None
    if body.template_id is not None:
        template = await get_active_template(db, body.template_id)
        if template is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Template is not available",
            )
        template_id = template.id

    # One run per (user, job, cv_version) — a repeat POST reuses the existing
    # run and the task re-claims nothing, so no duplicate pipeline is queued.
    run, created = await get_or_create_run(
        db, user_id, match.job_id, cv_version.id
    )
    await db.commit()

    evidence_match_task.delay(
        user_id, str(match.job_id), str(template_id) if template_id else None
    )

    return CreateTailoredCVAccepted(
        run_id=run.id,
        detail=(
            "Tailoring queued"
            if created
            else "Tailoring already queued for this CV and job"
        ),
    )


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
    if tailored_cv.status != TailoredCVStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approved tailored CVs can be rendered",
        )
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
