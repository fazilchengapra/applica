"""Unit tests for the retrieval layer (vector query + context builder)."""

from types import SimpleNamespace

from sqlalchemy.dialects import postgresql

from app.modules.rag.repositories.vector import build_chunk_search
from app.modules.rag.services.retrieval import build_context


def _compile(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


def _chunk(index=0, content="refund within 30 days"):
    return SimpleNamespace(
        doc_type="policy",
        access_level="internal",
        chunk_index=index,
        content=content,
    )


class TestBuildChunkSearch:
    def test_orders_by_cosine_distance_and_limits(self):
        sql = _compile(build_chunk_search([0.1] * 1024, top_k=5))

        assert "<=>" in sql
        assert "IS NOT NULL" in sql
        assert "LIMIT" in sql

    def test_filters_on_access_levels_when_given(self):
        sql = _compile(build_chunk_search([0.1] * 1024, access_levels=["internal"]))

        assert "access_level IN" in sql


class TestBuildContext:
    def test_joins_chunks_with_source_headers(self):
        context = build_context([_chunk(0), _chunk(1, "damaged items refunded")])

        assert context == (
            "[policy | access=internal | #0]\nrefund within 30 days\n\n"
            "[policy | access=internal | #1]\ndamaged items refunded"
        )

    def test_empty_context_for_no_chunks(self):
        assert build_context([]) == ""