"""Layout checks on a real PDF, plus the geometry predicate in isolation.

The predicate is unit-tested against synthetic line tuples as well as real
PDFs: PyMuPDF groups side-by-side text on a shared baseline into a single
*block*, so only line-level geometry can tell the two columns apart.
"""

import fitz

from app.modules.ats.constants import CheckStatus
from app.modules.ats.rules.parsability import (
    _lines_are_two_columns,
    check_parsability,
)


def _by_id(results, check_id):
    return next(r for r in results if r.id == check_id)


def _single_column_pdf(lines: list[str]) -> bytes:
    document = fitz.open()
    page = document.new_page()
    for index, line in enumerate(lines):
        page.insert_text((60, 80 + index * 16), line)
    payload = document.tobytes()
    document.close()
    return payload


def _two_column_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page()
    for index in range(12):
        page.insert_text((60, 80 + index * 16), f"Left column line {index} with words")
    for index in range(12):
        page.insert_text((340, 80 + index * 16), f"Right column line {index} words")
    payload = document.tobytes()
    document.close()
    return payload


def _line(x0, y0, x1, y1, text=""):
    return (x0, y0, x1, y1, text, 0, 0)


class TestColumnGeometry:
    def test_side_by_side_overlapping_lines_are_two_columns(self):
        blocks = [
            _line(50, 100, 250, 120, "left"),
            _line(50, 130, 250, 150, "left"),
            _line(50, 160, 250, 180, "left"),
            _line(50, 190, 250, 210, "left"),
            _line(340, 100, 540, 120, "right"),
            _line(340, 130, 540, 150, "right"),
            _line(340, 160, 540, 180, "right"),
            _line(340, 190, 540, 210, "right"),
        ]
        assert _lines_are_two_columns(blocks, 595.0) is True

    def test_a_stack_of_rows_is_not_two_columns(self):
        """Left-edge spread alone is not enough: a centred title already spreads."""
        blocks = [_line(60, 100 + i * 30, 500, 120 + i * 30, "row") for i in range(8)]
        assert _lines_are_two_columns(blocks, 595.0) is False

    def test_a_centred_title_above_the_body_is_not_two_columns(self):
        blocks = [_line(220, 80, 375, 100, "Ada Lovelace")]
        blocks += [_line(60, 120 + i * 30, 500, 140 + i * 30, "row") for i in range(6)]
        assert _lines_are_two_columns(blocks, 595.0) is False

    def test_too_few_lines_cannot_be_judged(self):
        blocks = [_line(50, 100, 250, 140, "a"), _line(340, 100, 540, 140, "b")]
        assert _lines_are_two_columns(blocks, 595.0) is False

    def test_a_zero_width_page_is_never_two_columns(self):
        blocks = [_line(0, 100 + i * 20, 100, 120 + i * 20, "x") for i in range(6)]
        assert _lines_are_two_columns(blocks, 0.0) is False


class TestCheckPasability:
    def test_a_text_based_single_column_cv_passes_layout(self):
        lines = [f"Experience bullet number {index} with a sensible amount of words" for index in range(40)]
        results = check_parsability(_single_column_pdf(lines))

        assert _by_id(results, "parsable_text_layer").status is CheckStatus.PASS
        assert _by_id(results, "single_column").status is CheckStatus.PASS
        assert _by_id(results, "page_count").status is CheckStatus.PASS

    def test_a_two_column_page_is_flagged(self):
        assert _by_id(check_parsability(_two_column_pdf()), "single_column").status is CheckStatus.FAIL

    def test_a_page_with_no_text_at_all_is_not_readable_by_an_ats(self):
        document = fitz.open()
        document.new_page()
        payload = document.tobytes()
        document.close()

        results = check_parsability(payload)
        assert _by_id(results, "parsable_text_layer").status is CheckStatus.FAIL
        assert _by_id(results, "single_column").status is CheckStatus.SKIPPED

    def test_a_missing_source_degrades_every_layout_check_to_skipped(self):
        results = check_parsability(None)
        assert len(results) == 3
        assert all(r.status is CheckStatus.SKIPPED for r in results)

    def test_an_unreadable_file_degrades_rather_than_raising(self):
        results = check_parsability(b"this is not a pdf")
        assert len(results) == 3
        assert all(r.status is CheckStatus.SKIPPED for r in results)

    def test_more_than_two_pages_is_penalised(self):
        document = fitz.open()
        for _ in range(4):
            page = document.new_page()
            for index in range(40):
                page.insert_text((60, 80 + index * 16), f"Line {index} of body copy with words")
        payload = document.tobytes()
        document.close()

        result = _by_id(check_parsability(payload), "page_count")
        assert result.status is CheckStatus.FAIL
        assert result.value == "4 pages"
