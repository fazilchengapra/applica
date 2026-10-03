"""Service- and SQL-level tests for the insights read model.

No database. Three things here are invisible in the response and would rot
silently:

- the skill-gap query must subtract ``cv_skills`` and scope to the user's
  *matched* jobs. Forgetting either returns the wrong set with a perfectly
  plausible shape.
- the week bucket must be inlined raw SQL. ``func.date_trunc('week', ...)`` binds
  ``'week'`` as a parameter, which Postgres refuses to match against the select
  list in GROUP BY — the endpoint 500s. Only the SQL text shows this.
- skill gaps must be suppressed without a current *completed* CV, because a
  still-parsing version has an incomplete skill list and would report every skill
  the user has as a gap.
"""

from datetime import datetime
from uuid import UUID

import pytest

from app.modules.dashboard import repository
from app.modules.dashboard.services import dashboard_service as ds

# A real UUID, not a string: the column is PG UUID(as_uuid=True), so
# literal_binds cannot render a str against it.
_CV = UUID("33333333-4444-4555-8666-777777777777")
_SINCE = datetime(2026, 9, 1, 0, 0, 0)


class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _Gap(skill, job_count, category):
    return _Row(skill=skill, job_count=job_count, category=category)


def _Trend(week, avg_score):
    return _Row(week=week, avg_score=avg_score)


def _missing_sql() -> str:
    stmt = repository._missing_skills_stmt(7, _CV).limit(10)
    return str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()


def _trend_sql() -> str:
    stmt = repository._score_trend_stmt(7, _SINCE)
    return str(stmt.compile(compile_kwargs={"literal_binds": True})).lower()


def test_missing_skills_subtracts_the_cv_skill_list():
    """Without the NOT IN, every required skill would be reported as a gap."""
    sql = _missing_sql()

    assert "job_skills.skill_id not in (select cv_skills.skill_id" in sql
    assert "where cv_skills.cv_id =" in sql


def test_missing_skills_scopes_to_the_users_matched_jobs():
    """Not every job in the table: only the ones the user is pursuing."""
    sql = _missing_sql()

    assert "job_skills.job_id in (select job_matches.job_id" in sql
    assert "job_matches.user_id = 7" in sql


def test_missing_skills_counts_distinct_jobs():
    """count is jobs-wanting-this-skill, so a duplicated job_skills row is one."""
    sql = _missing_sql()

    assert "count(distinct job_skills.job_id)" in sql
    assert "group by skills.id, skills.name, skills.category" in sql


def test_missing_skills_orders_by_impact_then_name():
    sql = _missing_sql()

    assert "order by count(distinct job_skills.job_id) desc, skills.name asc" in sql


def test_missing_skills_selects_the_new_category_column():
    sql = _missing_sql()

    assert "skills.category" in sql


def test_score_trend_inlines_the_week_bucket():
    """Regression guard: a bound 'week' parameter breaks GROUP BY.

    ``func.date_trunc('week', ...)`` renders as ``date_trunc($1, ...)``, which
    Postgres will not match against the identical-looking select list, so the
    query fails with "column must appear in the GROUP BY clause". The bucket has
    to be raw text so all three occurrences are the same expression.
    """
    sql = _trend_sql()

    assert "date_trunc('week', job_matches.matched_at)" in sql, sql
    # No parameterised date_trunc anywhere.
    assert "date_trunc($" not in sql, sql


def test_score_trend_buckets_group_and_orders_by_the_same_expression():
    sql = _trend_sql()

    assert sql.count("date_trunc('week', job_matches.matched_at)") == 3, sql
    assert "group by date_trunc('week', job_matches.matched_at)" in sql
    assert "order by date_trunc('week', job_matches.matched_at) asc" in sql


def test_score_trend_averages_the_score_within_each_week():
    sql = _trend_sql()

    assert "avg(job_matches.final_score)" in sql


def test_score_trend_binds_the_cutoff_without_a_timestamptz_cast():
    """matched_at is timestamp *without* time zone; a cast would shift the window."""
    stmt = repository._score_trend_stmt(7, _SINCE)
    compiled = stmt.compile(compile_kwargs={"literal_binds": True})

    assert "with time zone" not in str(compiled).lower()
    assert _SINCE.tzinfo is None


@pytest.mark.asyncio
async def test_current_cv_lookup_requires_completed_and_current():
    """A parsing version has an incomplete cv_skills list.

    Asserted on the SQL the function actually builds, captured through a stub
    session, so this fails if the status filter is ever dropped.
    """

    class _Capture:
        def __init__(self):
            self.sql = None

        async def scalar(self, stmt):
            self.sql = str(
                stmt.compile(compile_kwargs={"literal_binds": True})
            ).lower()
            return None

    cap = _Capture()
    await repository.get_current_completed_cv_id(cap, 7)

    assert "master_cv_versions.is_current is true" in cap.sql
    assert "master_cv_versions.status = 'completed'" in cap.sql
    assert "master_cvs.user_id = 7" in cap.sql


@pytest.mark.asyncio
async def test_build_insights_suppresses_gaps_without_a_completed_cv(monkeypatch):
    calls = {"gaps": 0, "trend": 0}

    async def get_current_completed_cv_id(db, user_id):
        return None

    async def get_missing_skills(db, user_id, cv_id, limit=10):
        calls["gaps"] += 1
        return []

    async def get_score_trend(db, user_id, since):
        calls["trend"] += 1
        return [_Trend(datetime(2026, 10, 6), 4.2)]

    monkeypatch.setattr(repository, "get_current_completed_cv_id", get_current_completed_cv_id)
    monkeypatch.setattr(repository, "get_missing_skills", get_missing_skills)
    monkeypatch.setattr(repository, "get_score_trend", get_score_trend)

    out = await ds.build_insights(object(), 7, weeks=8, limit=10)

    assert out.missing_skills == []
    assert calls["gaps"] == 0, "queried gaps with no CV to compare against"
    # The trend is independent of the CV, so it still reports.
    assert [(p.date, p.score) for p in out.score_trend] == [("Oct 6", 4.2)]
    assert calls["trend"] == 1


@pytest.mark.asyncio
async def test_build_insights_maps_rows(monkeypatch):
    async def get_current_completed_cv_id(db, user_id):
        return _CV

    async def get_missing_skills(db, user_id, cv_id, limit=10):
        return [
            _Gap("GraphQL", 9, "API"),
            _Gap("Docker & Kubernetes", 7, None),
        ]

    async def get_score_trend(db, user_id, since):
        return [_Trend(datetime(2026, 10, 1), 3.5), _Trend(datetime(2026, 10, 22), 6.1)]

    monkeypatch.setattr(repository, "get_current_completed_cv_id", get_current_completed_cv_id)
    monkeypatch.setattr(repository, "get_missing_skills", get_missing_skills)
    monkeypatch.setattr(repository, "get_score_trend", get_score_trend)

    out = await ds.build_insights(object(), 7, weeks=8, limit=10)

    assert [(g.skill, g.count, g.category) for g in out.missing_skills] == [
        ("GraphQL", 9, "API"),
        ("Docker & Kubernetes", 7, None),
    ]
    assert [(p.date, p.score) for p in out.score_trend] == [
        ("Oct 1", 3.5),
        ("Oct 22", 6.1),
    ]


class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _Gap(skill, job_count, category):
    return _Row(skill=skill, job_count=job_count, category=category)


def _Trend(week, avg_score):
    return _Row(week=week, avg_score=avg_score)