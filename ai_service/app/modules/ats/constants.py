"""Check catalogue, weights and the ruleset version for ATS readiness scoring.

A report's score is a weighted sum over the checks below.  Rules assign every
point; models only emit verdicts that a rule converts into a score.  Bump
``RULESET_VERSION`` whenever a rule's behaviour or a weight changes -- reports
record the version they were computed under, so a tuning pass never silently
rewrites a stored score and makes a user's CV look like it regressed.
"""

import enum
from dataclasses import dataclass

RULESET_VERSION = 1


class CheckStatus(str, enum.Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIPPED = "skipped"


class CheckKind(str, enum.Enum):
    RULE = "rule"
    HYBRID = "hybrid"
    LLM = "llm"


@dataclass(frozen=True)
class CheckSpec:
    id: str
    category: str
    label: str
    weight: int
    kind: CheckKind


CATEGORY_LABELS: dict[str, str] = {
    "contact": "Contact details",
    "sections": "Structure completeness",
    "keywords": "Role keywords",
    "impact": "Impact statements",
    "structure": "Consistency",
    "parsability": "Source document",
    "integrity": "Parsed data integrity",
}

CATEGORY_ORDER: tuple[str, ...] = (
    "contact",
    "sections",
    "keywords",
    "impact",
    "structure",
    "parsability",
    "integrity",
)

CHECK_SPECS: tuple[CheckSpec, ...] = (
    CheckSpec("contact_name", "contact", "Name present", 2, CheckKind.RULE),
    CheckSpec("contact_email", "contact", "Email present", 2, CheckKind.RULE),
    CheckSpec("contact_phone", "contact", "Phone present", 2, CheckKind.RULE),
    CheckSpec("contact_location", "contact", "Location present", 2, CheckKind.RULE),
    CheckSpec("contact_links", "contact", "Profile link present", 2, CheckKind.RULE),
    CheckSpec("section_experience", "sections", "Experience section", 5, CheckKind.RULE),
    CheckSpec("section_education", "sections", "Education section", 4, CheckKind.RULE),
    CheckSpec("section_summary", "sections", "Summary section", 3, CheckKind.RULE),
    CheckSpec("section_skills", "sections", "Skills section", 3, CheckKind.RULE),
    CheckSpec("role_keyword_coverage", "keywords", "Keyword coverage", 22, CheckKind.HYBRID),
    CheckSpec("role_alignment", "keywords", "Role alignment", 8, CheckKind.LLM),
    CheckSpec("impact_statements", "impact", "Quantified impact", 14, CheckKind.HYBRID),
    CheckSpec("action_verbs", "impact", "Action verbs", 6, CheckKind.RULE),
    CheckSpec("date_completeness", "structure", "Dates complete", 5, CheckKind.RULE),
    CheckSpec("employment_gaps", "structure", "Employment gaps", 5, CheckKind.RULE),
    CheckSpec("bullet_length", "structure", "Bullet length", 5, CheckKind.RULE),
    CheckSpec("parsable_text_layer", "parsability", "Extractable text layer", 5, CheckKind.RULE),
    CheckSpec("single_column", "parsability", "Single column layout", 3, CheckKind.RULE),
    CheckSpec("page_count", "parsability", "Page count", 2, CheckKind.RULE),
    # Weight 0: a mismatch means our structuring pass drifted from the uploaded
    # file, not that the CV is bad.  It is reported so the user can see it, but
    # it must never move the score.
    CheckSpec("data_integrity", "integrity", "Parsed data matches source", 0, CheckKind.RULE),
)

CHECKS_BY_ID: dict[str, CheckSpec] = {spec.id: spec for spec in CHECK_SPECS}


def category_weight(category: str) -> int:
    return sum(spec.weight for spec in CHECK_SPECS if spec.category == category)
