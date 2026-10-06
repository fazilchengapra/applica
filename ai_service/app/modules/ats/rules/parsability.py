"""Layout checks on the uploaded source PDF, via PyMuPDF.

This is the only part of the catalogue that can speak to how a parser *reads*
the file rather than what it says.  It runs on the master CV's own PDF; the
file is fetched best-effort, and a fetch failure degrades these checks to
``skipped`` rather than to a penalty the user cannot fix.
"""

from app.modules.ats.constants import CheckStatus
from app.modules.ats.rules.text import missing, present
from app.modules.ats.rules.types import CheckResult, skipped

MIN_CHARS_PER_PAGE = 100
STRONG_CHARS_PER_PAGE = 300
_MIN_LINES = 4
_COLUMN_X_SPREAD = 0.25
_COLUMN_X_TOLERANCE = 0.15


def check_parsability(pdf_bytes: bytes | None) -> list[CheckResult]:
    if not pdf_bytes:
        reason = "The source PDF could not be fetched, so no layout checks were run."
        return [
            skipped("parsable_text_layer", reason),
            skipped("single_column", reason),
            skipped("page_count", reason),
        ]

    try:
        import fitz

        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = list(document)
        per_page_chars = [len(page.get_text().strip()) for page in pages]
        line_lists = [_page_lines(page) for page in pages]
        total_lines = sum(len(lines) for lines in line_lists)
        column_pages = sum(
            1
            for lines, page in zip(line_lists, pages)
            if _lines_are_two_columns(lines, page.rect.width)
        )
        document.close()
    except Exception:
        reason = "The source PDF could not be read, so no layout checks were run."
        return [
            skipped("parsable_text_layer", reason),
            skipped("single_column", reason),
            skipped("page_count", reason),
        ]

    return [
        _text_layer_check(per_page_chars),
        _column_check(column_pages, len(pages), total_lines),
        _page_count_check(len(pages)),
    ]


def _text_layer_check(per_page_chars: list[int]) -> CheckResult:
    if not per_page_chars:
        return missing(
            "parsable_text_layer",
            "Empty document",
            "The PDF contains no pages. Re-upload the correct file.",
        )

    total = sum(per_page_chars)
    average = total / len(per_page_chars)

    if average >= STRONG_CHARS_PER_PAGE:
        return present(
            "parsable_text_layer",
            "Text based",
            "",
            evidence={"pages": len(per_page_chars), "chars": total},
        )
    if average >= MIN_CHARS_PER_PAGE:
        return CheckResult(
            id="parsable_text_layer",
            status=CheckStatus.WARN,
            score=0.5,
            value="Sparse text",
            detail=(
                "Extracting far less text than expected. This is usually a scanned or "
                "image-based PDF, which most ATS read as blank."
            ),
            evidence={"pages": len(per_page_chars), "chars": total},
        )
    return missing(
        "parsable_text_layer",
        "Likely image based",
        "Almost no text is extractable, so an ATS parsing this file would find an empty CV. "
        "Export from a text editor rather than scanning.",
        evidence={"pages": len(per_page_chars), "chars": total},
    )


def _column_check(column_pages: int, page_count: int, total_lines: int) -> CheckResult:
    if page_count == 0:
        return skipped("single_column", "The source PDF contains no pages.")
    if total_lines < _MIN_LINES:
        return skipped(
            "single_column",
            "Too little extractable text to tell how the page is laid out.",
        )

    share = column_pages / page_count
    if column_pages == 0:
        return present(
            "single_column",
            "Single column",
            "",
            evidence={"pages": page_count},
        )
    if share <= 0.5:
        return CheckResult(
            id="single_column",
            status=CheckStatus.WARN,
            score=0.5,
            value=f"{column_pages} of {page_count} pages split",
            detail=(
                "Text blocks sit side by side on part of the document. Parsers that read "
                "top-to-bottom will interleave the two columns."
            ),
            evidence={"pages": page_count, "column_pages": column_pages},
        )
    return missing(
        "single_column",
        "Multi-column",
        "More than half the document reads as two columns. Most ATS extract text line by "
        "line and will produce interleaved, unreadable output.",
        evidence={"pages": page_count, "column_pages": column_pages},
    )


def _page_count_check(page_count: int) -> CheckResult:
    if page_count <= 0:
        return skipped("page_count", "The source PDF contains no pages.")
    if page_count == 1:
        return present("page_count", "1 page", evidence={"pages": page_count})
    if page_count == 2:
        return CheckResult(
            id="page_count",
            status=CheckStatus.PASS,
            score=0.7,
            value="2 pages",
            detail="Two pages is normal for experienced candidates; keep the most relevant material first.",
            evidence={"pages": page_count},
        )
    if page_count == 3:
        return CheckResult(
            id="page_count",
            status=CheckStatus.WARN,
            score=0.3,
            value="3 pages",
            detail="Beyond two pages most readers stop at page one, and some parsers truncate long files.",
            evidence={"pages": page_count},
        )
    return missing(
        "page_count",
        f"{page_count} pages",
        "Four or more pages is well past what recruiters or parsers will consume. Cut to the work that matters.",
        evidence={"pages": page_count},
    )


def _page_lines(page) -> list[tuple]:
    """Every non-empty text line on the page, as ``(x0, y0, x1, y1, text)``.

    ``get_text("blocks")`` merges side-by-side text on a shared baseline into
    one wide block, so a real two-column page arrives as a single block and
    would never be detected.  Lines survive the split.
    """
    payload = page.get_text("dict")
    lines: list[tuple] = []
    for block in payload.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            bbox = line.get("bbox")
            text = "".join(span.get("text", "") for span in line.get("spans", []))
            if bbox and text.strip():
                lines.append((bbox[0], bbox[1], bbox[2], bbox[3], text))
    return lines


def _lines_are_two_columns(lines: list, page_width: float) -> bool:
    """Two columns means lines at different left edges that overlap vertically.

    A left-edge spread alone is not enough -- a centred name and a left-aligned
    body already look wide apart, and a single-column page never stacks two
    lines on the same band of the page.  Vertical overlap is what actually
    distinguishes side-by-side text from one flowing column.
    """
    if not page_width:
        return False

    usable = [line for line in lines if line[4] and line[4].strip() and (line[3] - line[1]) > 2]
    if len(usable) < _MIN_LINES:
        return False

    lefts = [line[0] for line in usable]
    if max(lefts) - min(lefts) < _COLUMN_X_SPREAD * page_width:
        return False

    for index, first in enumerate(usable):
        for second in usable[index + 1 :]:
            if abs(first[0] - second[0]) < _COLUMN_X_TOLERANCE * page_width:
                continue
            if first[1] < second[3] - 2 and second[1] < first[3] - 2:
                return True
    return False
