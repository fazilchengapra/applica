"""HTTP API for the user dashboard aggregate."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id
from app.db.session import get_db
from app.modules.dashboard.schemas import (
    DashboardResponse,
    DashboardStatsResponse,
    InsightResponse,
    TailoringRunListOut,
    TopMatchListOut,
)
from app.modules.dashboard.services.dashboard_service import (
    build_dashboard,
    build_dashboard_stats,
    build_insights,
    build_tailoring_runs,
    build_top_matches,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Everything the dashboard renders, scoped to the caller.

    Always 200: an account with no CV, matches or tailored CVs gets a fully
    shaped, zeroed response so the client never has to handle a 404 or a null
    section.
    """
    return await build_dashboard(db, user_id)


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    top_n: int = Query(
        10,
        ge=1,
        le=100,
        description="Page size echoed back for the client's match-card fetch",
    ),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Headline counters for the dashboard tiles, scoped to the caller.

    The cheap sibling of ``GET /dashboard``: three aggregates, no cards and no
    activity feed, so a client can poll the counters without re-fetching the
    whole aggregate.

    Always 200, and zeroed rather than null: an account with no matches gets
    ``average_final_score`` of 0.0 and empty buckets.
    """
    return await build_dashboard_stats(db, user_id, top_n)


@router.get("/top-matches", response_model=TopMatchListOut)
async def get_top_matches(
    limit: int = Query(3, ge=1, le=3),
    offset: int = Query(0, ge=0),
    min_score: float | None = Query(
        None,
        ge=0,
        description=(
            "Optional floor on final_score. Unset by default: the column is "
            "documented 0-1 but written 0-100, so any floor calibrated to one "
            "scale silently admits or excludes everything under the other."
        ),
    ),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """The user's highest-scoring matches, as a paginated table.

    Sibling of ``matches.top`` inside ``GET /dashboard``, but standalone and
    pageable: rows are flat (no nested job/company objects), carry the three
    stage scores the dashboard cards omit, and each report how far tailoring
    for that job has got.

    ``count`` is the total qualifying matches, not the length of this page.
    Always 200; an account with no matches gets ``count`` 0 and no results.
    """
    return await build_top_matches(db, user_id, min_score=min_score, limit=limit, offset=offset)


@router.get("/tailoring-runs", response_model=TailoringRunListOut)
async def get_tailoring_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """The user's tailoring runs, newest first, as a paginated table.

    Run-centric, so it also shows runs that have not produced a tailored CV yet —
    a queued run, or one that failed before the draft — with ``cv_id`` null.
    ``GET /tailored-cvs`` cannot show those, because it is keyed off
    ``tailored_cvs``.

    ``status`` is a presentation value: stored ``pending``/``processing`` both
    report as ``in_progress``. ``current_stage`` is a display label rather than
    the stored enum, and is never null.

    ``count`` is the total number of runs, not the length of this page. Always
    200; an account that has never tailored anything gets ``count`` 0 and no
    results.
    """
    return await build_tailoring_runs(db, user_id, limit=limit, offset=offset)


@router.get("/insights", response_model=InsightResponse)
async def get_insights(
    weeks: int = Query(
        8,
        ge=1,
        le=52,
        description="How many weeks back the score trend reaches.",
    ),
    limit: int = Query(
        10,
        ge=1,
        le=50,
        description="Maximum number of missing skills to return.",
    ),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Skill gaps and the match-score trend, for the dashboard insights section.

    ``missing_skills`` are skills the user's matched jobs require that their
    current CV does not list, most widely required first; ``count`` is how many
    of those jobs want it. ``category`` comes from ``skills.category`` and is
    null until that taxonomy is backfilled.

    Empty when the user has no current *completed* CV: a version still parsing has
    an incomplete skill list, so every skill would look like a gap.

    ``score_trend`` is the weekly mean ``final_score`` over the last ``weeks``
    weeks, Monday-aligned, labelled ``'Mon D'``. Weeks with no matches are
    omitted rather than sent as null. Scores carry the known 0-1 vs 0-100 scale
    inconsistency, so a point may exceed 1.

    Always 200; an account with no matches gets two empty lists.
    """
    return await build_insights(db, user_id, weeks=weeks, limit=limit)
