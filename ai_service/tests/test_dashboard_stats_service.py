"""Service- and mapping-level tests for the dashboard stats read model.

No database: the aggregation SQL is exercised against the real Postgres by the
endpoint itself, while these pin the two things that would otherwise rot
silently — the assembly of the tailored-CV counters, and the invariant that the
pipeline buckets partition ``MatchStatus``.
"""

import pytest

from app.modules.dashboard import repository
from app.modules.dashboard.schemas import MatchStatusBreakdown
from app.modules.dashboard.services.dashboard_service import build_dashboard_stats
from app.modules.matching.models.job_match import MatchStatus


def test_pipeline_buckets_partition_match_status():
    """Every MatchStatus member lands in exactly one bucket.

    This is what makes the five counts sum to ``total``. Adding a member to the
    enum without adding it to a bucket would silently drop those rows from the
    breakdown while leaving them in the total, so this fails loudly instead.
    """
    buckets = repository._MATCH_PIPELINE_BUCKETS

    seen = [status for statuses in buckets.values() for status in statuses]
    assert len(seen) == len(set(seen)), "a status is counted in two buckets"
    assert set(seen) == set(MatchStatus), (
        "MatchStatus members missing from the buckets: "
        f"{sorted(s.name for s in set(MatchStatus) - set(seen))}; "
        "unbucketed statuses: "
        f"{sorted(s.name for s in set(seen) - set(MatchStatus))}"
    )


def test_breakdown_requires_no_key_to_be_present():
    """Every bucket defaults to 0 so a partial dict still validates."""
    assert MatchStatusBreakdown().model_dump() == {
        "new": 0,
        "shortlisted": 0,
        "applied": 0,
        "interviewing": 0,
        "rejected": 0,
        "total": 0,
    }


@pytest.mark.asyncio
async def test_build_stats_maps_render_axis_onto_completed_and_in_progress(
    monkeypatch,
):
    """``rendered``/``rendering`` are the completed/in-progress figures.

    Asserted here because the rename is invisible in the response schema: both
    sides are plain ints, so a swap would pass a shape test and quietly
    inverts a dashboard tile.
    """

    async def get_match_pipeline_counts(db, user_id):
        return {
            "new": 1,
            "shortlisted": 0,
            "applied": 0,
            "interviewing": 0,
            "rejected": 0,
            "total": 1,
        }

    async def get_average_final_score(db, user_id):
        return 61.25

    async def get_tailored_cv_counts(db, user_id):
        return {
            "total": 9,
            "approved": 9,
            "failed": 0,
            "rendering": 3,  # pending + processing
            "rendered": 6,  # completed
        }

    monkeypatch.setattr(
        repository, "get_match_pipeline_counts", get_match_pipeline_counts
    )
    monkeypatch.setattr(repository, "get_average_final_score", get_average_final_score)
    monkeypatch.setattr(repository, "get_tailored_cv_counts", get_tailored_cv_counts)

    stats = await build_dashboard_stats(object(), 7, top_n=10)

    assert stats.tailored_cvs_completed == 6
    assert stats.tailored_cvs_in_progress == 3
    assert stats.average_final_score == 61.25
    assert stats.top_n == 10
    assert stats.match_status_breakdown.total == 1