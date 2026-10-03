"""Service- and SQL-level tests for the top-matches read model.

No database. The queries are exercised against the real Postgres when the
endpoint runs against the stack; what these pin is the two things that would
rot silently:

- the tailoring-progress mapping, whose steps are invisible in the response
  schema because both sides are plain strings, so a swap passes a shape test and
  quietly inverts a table cell; and
- the shape of the generated SQL, specifically that the tailoring run is read
  through a *scalar subquery* rather than a join. ``tailoring_runs`` is unique on
  ``(user_id, job_id, cv_version_id)``, not ``(user_id, job_id)``, so a join emits
  one row per run and inflates both ``count`` and the page. A SQL-shape test is
  the only thing standing between that regression and a silently wrong count.
"""

import pytest

from app.modules.dashboard import repository
from app.modules.dashboard.schemas import TailoredCVProgress
from app.modules.dashboard.services import dashboard_service as ds
from app.modules.tailoring.models import TailoringRunStatus


class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _compiled_top_matches_stmt():
    """SQL text of the statement the real query builder produces.

    Calls ``_top_matches_stmt`` rather than re-assembling the statement, so
    these assertions cannot drift away from what actually runs.
    """
    stmt = repository._top_matches_stmt(7).limit(20)
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


def test_top_matches_reads_the_run_through_a_scalar_subquery():
    """No JOIN to tailoring_runs — that is what would fan out.

    ``tailoring_runs`` allows several runs per (user, job) because its unique
    constraint includes ``cv_version_id``. Joining would multiply match rows, so
    ``count`` and the page would both be wrong once a user re-tailors after a
    new master CV. Asserted on the SQL text because that is the only place the
    regression would be visible.
    """
    sql = _compiled_top_matches_stmt().lower()

    assert "join tailoring_runs" not in sql
    assert "select tailoring_runs.status" in sql
    # correlated on the outer match's job, and newest-first
    assert "tailoring_runs.job_id = job_matches.job_id" in sql
    assert "order by tailoring_runs.created_at desc" in sql
    # LIMIT 1 keeps the subquery scalar
    assert sql.count("limit 1)") == 1


def test_top_matches_orders_by_score_with_a_stable_tiebreak():
    """Paging over a non-total order can repeat or drop rows at a boundary."""
    sql = _compiled_top_matches_stmt().lower()
    assert "order by job_matches.final_score desc, job_matches.matched_at desc" in sql


@pytest.mark.parametrize(
    "run_status,expected",
    [
        (TailoringRunStatus.pending, TailoredCVProgress.in_progress),
        (TailoringRunStatus.processing, TailoredCVProgress.in_progress),
        (TailoringRunStatus.completed, TailoredCVProgress.completed),
        (TailoringRunStatus.failed, TailoredCVProgress.failed),
        (None, TailoredCVProgress.none),
    ],
)
def test_run_status_maps_to_progress(run_status, expected):
    row = _Row(
        id="00000000-0000-0000-0000-000000000000",
        job_title="T",
        company_display_name="C",
        company_normalized_name="c",
        match_status="new",
        final_score=1.0,
        vector_score=None,
        lexical_score=None,
        rrf_score=None,
        key_matches=None,
        key_gaps=None,
        tailored_cv_status=run_status,
    )
    assert ds._to_top_match_result(row).tailored_cv_status is expected


def test_progress_covers_every_run_status():
    """A new TailoringRunStatus member must not silently become ``none``."""
    mapped = set(ds._RUN_STATUS_TO_PROGRESS)
    assert mapped == set(TailoringRunStatus)


@pytest.mark.asyncio
async def test_build_top_matches_reports_count_alongside_the_page(monkeypatch):
    """count is the total, so it must survive a short or empty page."""
    seen = {}

    async def count_top_matches(db, user_id, min_score=None):
        seen["count_args"] = (user_id, min_score)
        return 12

    async def get_top_match_results(db, user_id, min_score=None, limit=20, offset=0):
        seen["page_args"] = (user_id, min_score, limit, offset)
        return []

    monkeypatch.setattr(repository, "count_top_matches", count_top_matches)
    monkeypatch.setattr(repository, "get_top_match_results", get_top_match_results)

    out = await ds.build_top_matches(
        object(), 7, min_score=4.5, limit=5, offset=10
    )

    assert out.count == 12
    assert out.results == []
    assert seen["count_args"] == (7, 4.5)
    assert seen["page_args"] == (7, 4.5, 5, 10)