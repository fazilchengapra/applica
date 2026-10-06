"""Section-presence checks -- an ATS that cannot find a section scores it zero."""

from app.modules.ats.constants import CheckStatus
from app.modules.ats.rules.text import missing, present
from app.modules.ats.rules.types import CheckResult

# A missing Summary is a missed opportunity rather than a blocking defect: it
# is the only section a competent CV can legitimately omit.
_SECTIONS = (
    ("section_experience", "Experience", "experience", True),
    ("section_education", "Education", "education", True),
    ("section_summary", "Summary", "summary", False),
    ("section_skills", "Skills", "skills", True),
)


def _count(value) -> int:
    if isinstance(value, list):
        return len([item for item in value if item])
    if isinstance(value, str):
        return len(value.strip())
    return 0


def check_sections(parsed: dict) -> list[CheckResult]:
    results: list[CheckResult] = []
    for check_id, label, key, blocking in _SECTIONS:
        count = _count(parsed.get(key))
        if count > 0:
            results.append(present(check_id, f"{label} present", evidence={"count": count}))
        elif blocking:
            results.append(
                missing(
                    check_id,
                    f"No {label}",
                    f"Add a {label} section; a parser that cannot locate it "
                    "scores the whole section as absent.",
                )
            )
        else:
            results.append(
                CheckResult(
                    id=check_id,
                    status=CheckStatus.WARN,
                    score=0.4,
                    value=f"No {label}",
                    detail=(
                        "A short summary aimed at the target role is the fastest place "
                        "to put the terms a screen will search for."
                    ),
                )
            )
    return results
