"""Date completeness, employment-gap and bullet-length checks."""

import calendar
import re

from app.modules.ats.constants import CheckStatus
from app.modules.ats.rules.text import Bullet, missing, present
from app.modules.ats.rules.types import CheckResult

_MONTHS: dict[str, int] = {}
for _i in range(1, 13):
    _MONTHS[calendar.month_name[_i].lower()] = _i
    _MONTHS[calendar.month_name[_i][:3].lower()] = _i

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_ISO_MONTH = re.compile(r"\b(?:19|20)\d{2}[-/.](\d{1,2})\b")
_US_MONTH = re.compile(r"\b(\d{1,2})[-/.](?:19|20)\d{2}\b")

_PRESENT = {"present", "current", "now", "ongoing", "to date", "till date", "today"}

MIN_BULLET_CHARS = 40
MAX_BULLET_CHARS = 260


def parse_month(value, *, end: bool = False) -> tuple[int, int] | None:
    """Best-effort ``(year, month)`` for a CV date string.

    A year with no month is expanded outward -- to January for a start date and
    to December for an end date -- so an unparseable month can only ever shrink
    a gap, never invent one.
    """
    text = str(value or "").strip().lower()
    if not text or text in _PRESENT:
        return None

    year_match = _YEAR.search(text)
    if not year_match:
        return None
    year = int(year_match.group(0))

    month: int | None = None
    iso = _ISO_MONTH.search(text)
    if iso:
        month = int(iso.group(1))
    if month is None:
        us = _US_MONTH.search(text)
        if us:
            month = int(us.group(1))
    if month is None:
        for name, number in _MONTHS.items():
            if name and name in text:
                month = number
                break
    if month is None or not 1 <= month <= 12:
        return (year, 12 if end else 1)
    return (year, month)


def _months_between(start: tuple[int, int], end: tuple[int, int]) -> int:
    return (end[0] - start[0]) * 12 + (end[1] - start[1])


def check_date_completeness(parsed: dict) -> CheckResult:
    entries = [e for e in (parsed.get("experience") or []) if isinstance(e, dict)]
    if not entries:
        return CheckResult(
            id="date_completeness",
            status=CheckStatus.SKIPPED,
            score=0.0,
            value="No entries",
            detail="No experience entries were parsed, so date coverage cannot be measured.",
        )

    incomplete = [
        f"{e.get('title') or 'entry'} ({e.get('company') or 'unknown'})"
        for e in entries
        if not e.get("start_date")
        or (not e.get("is_current") and not e.get("end_date"))
    ]

    if not incomplete:
        return present("date_completeness", "All dated", evidence={"entries": len(entries)})

    return missing(
        "date_completeness",
        f"{len(incomplete)} undated",
        "Dates are optional to parsers but recruiters filter on them; "
        "an entry without a start or end date reads as an unexplained gap: "
        + ", ".join(incomplete[:5]),
        evidence={"incomplete": incomplete},
    )


def check_employment_gaps(parsed: dict) -> CheckResult:
    entries = [e for e in (parsed.get("experience") or []) if isinstance(e, dict)]

    spans: list[tuple[tuple[int, int], tuple[int, int] | None]] = []
    for entry in entries:
        start = parse_month(entry.get("start_date"), end=False)
        if start is None:
            continue
        end = None if entry.get("is_current") else parse_month(entry.get("end_date"), end=True)
        spans.append((start, end))

    if len(spans) < 2:
        return CheckResult(
            id="employment_gaps",
            status=CheckStatus.SKIPPED,
            score=0.0,
            value="Not checked",
            detail="Fewer than two dated roles, so no gap between them can be measured.",
        )

    spans.sort(key=lambda span: span[0])

    gaps: list[int] = []
    for (_start, end), (next_start, _next_end) in zip(spans, spans[1:]):
        if end is None:
            continue
        gaps.append(max(0, _months_between(end, next_start)))

    if not gaps:
        return CheckResult(
            id="employment_gaps",
            status=CheckStatus.SKIPPED,
            score=0.0,
            value="Not checked",
            detail="No closed role boundary was parseable, so no gap could be measured.",
        )

    longest = max(gaps)
    if longest <= 2:
        return present("employment_gaps", "No material gaps", evidence={"longest_months": longest})
    if longest <= 6:
        return CheckResult(
            id="employment_gaps",
            status=CheckStatus.WARN,
            score=0.6,
            value=f"{longest}-month gap",
            detail=(
                "Short gaps are normal. Anything past three months should be explained "
                "in the summary so a recruiter reads it as a choice rather than a missing period."
            ),
            evidence={"longest_months": longest},
        )
    return CheckResult(
        id="employment_gaps",
        status=CheckStatus.FAIL,
        score=0.15,
        value=f"{longest}-month gap",
        detail=(
            "A gap this long will be asked about in screening. State what happened -- "
            "caregiving, study, freelance, layoff -- somewhere in the CV."
        ),
        evidence={"longest_months": longest},
    )


def check_bullet_length(bullets: list[Bullet]) -> CheckResult:
    if not bullets:
        return CheckResult(
            id="bullet_length",
            status=CheckStatus.SKIPPED,
            score=0.0,
            value="No bullets",
            detail="No experience bullets were parsed, so length cannot be measured.",
        )

    out_of_range = [
        {"ref": b.ref, "chars": len(b.text)}
        for b in bullets
        if not MIN_BULLET_CHARS <= len(b.text) <= MAX_BULLET_CHARS
    ]
    score = (len(bullets) - len(out_of_range)) / len(bullets)

    if not out_of_range:
        return present("bullet_length", "All in range", evidence={"bullets": len(bullets)})
    if score >= 0.7:
        status, value = CheckStatus.WARN, f"{len(out_of_range)} too long or short"
        detail = (
            f"Bullets work best between {MIN_BULLET_CHARS} and {MAX_BULLET_CHARS} characters. "
            "Very long lines get truncated by some parsers and skimmed by all readers."
        )
    else:
        status, value = CheckStatus.FAIL, f"{len(out_of_range)} of {len(bullets)} off"
        detail = (
            f"Most bullets fall outside {MIN_BULLET_CHARS}-{MAX_BULLET_CHARS} characters. "
            "Either they are run-on paragraphs or fragments that say nothing."
        )

    return CheckResult(
        id="bullet_length",
        status=status,
        score=score,
        value=value,
        detail=detail,
        evidence={"outliers": out_of_range[:10], "bullets": len(bullets)},
    )
