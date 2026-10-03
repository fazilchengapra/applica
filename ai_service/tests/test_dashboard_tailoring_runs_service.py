"""Service- and SQL-level tests for the tailoring-runs read model.

No database. Two things here would rot silently:

- the ``tailored_cvs`` join must stay an *outer* join. It is the difference
  between "this run has not produced a CV yet" (``cv_id`` null, row still listed)
  and "this run does not exist" (row dropped), and the response looks fine either
  way for the rows that do survive — so only a SQL assertion catches it; and
- both presentation maps must cover their whole enum. ``status`` and
  ``current_stage`` are strings in the response, so a missing entry renders as a
  plausible-looking wrong value instead of failing.
"""

import pytest
from datetime import datetime, timezone

from app.modules.dashboard import repository
from app.modules.dashboard.schemas import TailoredCVProgress, TailoringStageLabel
from app.modules.dashboard.services import dashboard_service as ds
from app.modules.tailoring.models import TailoringRunStatus, TailoringStage

_TS = datetime(2026, 10, 3, 9, 20, 0, tzinfo=timezone.utc)


class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _row(**overrides):
    base = dict(
        id="00000000-0000-0000-0000-000000000000",
        run_status=TailoringRunStatus.completed,
        run_stage=TailoringStage.write,
        created_at=_TS,
        updated_at=_TS,
        error_message=None,
        tailored_cv_id=None,
        job_title="T",
        company_display_name="C",
        company_normalized_name="c",
    )
    base.update(overrides)
    return _Row(**base)


def _compiled_stmt():
    stmt = repository._tailoring_runs_stmt(7).limit(20)
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


def test_tailoring_runs_outer_joins_tailored_cvs():
    """An inner join would silently drop every run that has no CV yet.

    A run that is still queued, or that failed before the draft was written, has
    no ``tailored_cvs`` row. The endpoint exists to show those runs, so the join
    has to be a LEFT OUTER JOIN.
    """
    sql = _compiled_stmt().lower()

    assert "left outer join tailored_cvs" in sql
    assert "tailored_cvs.tailoring_run_id = tailoring_runs.id" in sql


def test_tailoring_runs_inner_joins_job_and_company():
    """Both are NOT NULL FKs on tailoring_runs/jobs, so no row is lost."""
    sql = _compiled_stmt().lower()

    assert "join jobs on jobs.id = tailoring_runs.job_id" in sql
    assert "join companies on companies.id = jobs.company_id" in sql


def test_tailoring_runs_orders_newest_first_with_a_stable_tiebreak():
    """Two runs can share created_at, since the column defaults to now()."""
    sql = _compiled_stmt().lower()

    assert (
        "order by tailoring_runs.created_at desc, tailoring_runs.id desc" in sql
    ), sql[-160:]


def test_stage_labels_cover_every_stage():
    """A new TailoringStage must fail here, not render as a wrong label."""
    assert set(ds._STAGE_TO_LABEL) == set(TailoringStage)
    assert set(ds._STAGE_TO_LABEL.values()) == set(TailoringStageLabel)


def test_stage_labels_are_distinct():
    """Two stages sharing a label would make the column ambiguous."""
    assert len(ds._STAGE_TO_LABEL) == len(TailoringStageLabel)


def test_run_status_map_covers_every_run_status():
    assert set(ds._RUN_STATUS_TO_PROGRESS) == set(TailoringRunStatus)


@pytest.mark.parametrize(
    "stage,expected",
    [
        (TailoringStage.evidence_match, TailoringStageLabel.evidence_matcher),
        (TailoringStage.strategy, TailoringStageLabel.strategist),
        (TailoringStage.write, TailoringStageLabel.writer),
        (TailoringStage.critic, TailoringStageLabel.critic),
    ],
)
def test_stage_maps_to_label(stage, expected):
    assert ds._to_tailoring_run_item(_row(run_stage=stage)).current_stage is expected


@pytest.mark.parametrize(
    "run_status,expected",
    [
        (TailoringRunStatus.pending, TailoredCVProgress.in_progress),
        (TailoringRunStatus.processing, TailoredCVProgress.in_progress),
        (TailoringRunStatus.completed, TailoredCVProgress.completed),
        (TailoringRunStatus.failed, TailoredCVProgress.failed),
    ],
)
def test_run_status_maps_to_progress(run_status, expected):
    assert ds._to_tailoring_run_item(_row(run_status=run_status)).status is expected


@pytest.mark.asyncio
async def test_build_tailoring_runs_reports_total_alongside_the_page(monkeypatch):
    seen = {}

    async def count_tailoring_runs(db, user_id):
        seen["count_args"] = user_id
        return 42

    async def get_tailoring_runs(db, user_id, limit=20, offset=0):
        seen["page_args"] = (user_id, limit, offset)
        return []

    monkeypatch.setattr(repository, "count_tailoring_runs", count_tailoring_runs)
    monkeypatch.setattr(repository, "get_tailoring_runs", get_tailoring_runs)

    out = await ds.build_tailoring_runs(object(), 7, limit=5, offset=10)

    assert out.count == 42
    assert out.results == []
    assert seen["count_args"] == 7
    assert seen["page_args"] == (7, 5, 10)