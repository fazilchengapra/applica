"""Orchestration for one ATS readiness analysis.

Order matters: every deterministic rule runs first against the stored CV, then
the two model-dependent checks are attempted, then the source PDF is fetched
for layout. Any layer that fails degrades to ``skipped`` -- the report is always
produced, and ``semantic_verified`` records whether the semantic layer answered.
"""

import asyncio
import hashlib
import json
import logging
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ats.constants import CHECKS_BY_ID, RULESET_VERSION, CheckStatus
from app.modules.ats.exceptions import ATSCVNotFoundError, ATSCVNotReadyError
from app.modules.ats.models import ATSReport
from app.modules.ats.repository import (
    delete_report,
    find_current_cv_version,
    find_owned_cv_version,
    get_report,
    get_report_owned,
    list_reports as query_reports,
)
from app.modules.ats.rules import (
    contact,
    impact,
    integrity,
    keywords,
    parsability,
    sections,
    structure,
)
from app.modules.ats.rules.impact import metric_candidate_bullets
from app.modules.ats.rules.text import Bullet, collect_bullets
from app.modules.ats.rules.types import CheckResult, skipped
from app.modules.ats.schemas import (
    ATSReportListItem,
    ATSReportListOut,
    ATSReportOut,
    CheckOut,
    InsightOut,
)
from app.modules.ats.services.score_aggregator import aggregate, check_sort_key
from app.modules.ats.services.semantic_judge import SemanticJudgment, judge_semantics
from app.modules.ats.services.role_vocabulary import resolve_role_vocabulary

logger = logging.getLogger(__name__)

# A CV never carries this many bullets; the cap keeps one call inside the
# context window rather than silently truncating mid-analysis.
MAX_BULLETS_FOR_LLM = 60


def content_hash(raw_text: str | None, parsed_data: dict | None) -> str:
    payload = json.dumps(
        {"text": raw_text or "", "parsed": parsed_data or {}},
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _check_payload(result: CheckResult) -> dict:
    spec = CHECKS_BY_ID[result.id]
    return {
        "id": result.id,
        "label": spec.label,
        "category": spec.category,
        "weight": spec.weight,
        "kind": spec.kind.value,
        "status": result.status.value,
        "score": min(1.0, max(0.0, result.score)),
        "value": result.value,
        "detail": result.detail,
        "evidence": result.evidence,
    }


def _download_source_pdf(s3_key: str | None) -> bytes | None:
    if not s3_key:
        return None
    try:
        from app.modules.master_cv.services.helpers.s3_downloader import download_pdf_from_s3

        return download_pdf_from_s3(s3_key)
    except Exception as exc:
        logger.warning("Could not fetch source PDF for layout checks: %s", exc)
        return None


def _impact_from_model(judged: list[Bullet], judgment: SemanticJudgment) -> CheckResult:
    verdicts = {v.ref: v.real_impact for v in judgment.bullet_verdicts}
    verified = [b for b in judged if verdicts.get(b.ref)]
    score = len(verified) / len(judged)
    ratio_candidates = metric_candidate_bullets(judged)

    if score >= 0.6:
        status, value = CheckStatus.PASS, "Strong"
        detail = ""
    elif score >= 0.3:
        status, value = CheckStatus.WARN, f"{len(verified)} of {len(judged)}"
        detail = "Only a minority of bullets attach a measurable outcome to the work."
    else:
        status, value = CheckStatus.FAIL, "Add metrics"
        detail = (
            "Few bullets quantify what changed. Add the figure that proves the "
            "result -- percentage, revenue, time saved, volume handled."
        )

    return CheckResult(
        id="impact_statements",
        status=status,
        score=score,
        value=value,
        detail=detail,
        evidence={
            "verified_refs": [b.ref for b in verified],
            "candidate_refs": [b.ref for b in ratio_candidates],
            "judged": len(judged),
            "verified": True,
        },
    )


def _impact_from_regex(bullets: list[Bullet]) -> CheckResult:
    """Lower bound used when the semantic model did not answer.

    Regex cannot tell an achievement from an incidental number, so this only
    reports how many bullets *contain* a figure -- never that they are
    achievements. ``semantic_verified`` on the report says so explicitly.
    """
    if not bullets:
        return CheckResult(
            id="impact_statements",
            status=CheckStatus.SKIPPED,
            score=0.0,
            value="No bullets",
            detail="No experience bullets were parsed, so impact cannot be measured.",
        )

    candidates = metric_candidate_bullets(bullets)
    score = len(candidates) / len(bullets)

    if score >= 0.6:
        status, value = CheckStatus.PASS, f"{len(candidates)} of {len(bullets)}"
    elif score >= 0.3:
        status, value = CheckStatus.WARN, f"{len(candidates)} of {len(bullets)}"
    else:
        status, value = CheckStatus.FAIL, "Add metrics"

    return CheckResult(
        id="impact_statements",
        status=status,
        score=score,
        value=value,
        detail=(
            "Counted bullets containing a figure. These were not confirmed as real "
            "achievements because the semantic model was unavailable."
        ),
        evidence={
            "candidate_refs": [b.ref for b in candidates],
            "bullets": len(bullets),
            "verified": False,
        },
    )


def _alignment_result(judgment: SemanticJudgment | None) -> CheckResult:
    if judgment is None:
        return skipped(
            "role_alignment",
            "The semantic model was unavailable, so role fit was not judged.",
        )
    if judgment.role_aligned:
        return CheckResult(
            id="role_alignment",
            status=CheckStatus.PASS,
            score=1.0,
            value="Strong fit",
            detail=judgment.role_alignment_reason,
            evidence={"aligned": True},
        )
    return CheckResult(
        id="role_alignment",
        status=CheckStatus.FAIL,
        score=0.0,
        value="Weak role fit",
        detail=judgment.role_alignment_reason
        or (
            "The CV does not read as a fit for this target role. Retarget the "
            "summary and lead with role-relevant work."
        ),
        evidence={"aligned": False},
    )


def _run_deterministic(
    parsed: dict, raw_text: str | None
) -> tuple[list[CheckResult], list[Bullet]]:
    bullets = collect_bullets(parsed)
    results: list[CheckResult] = []
    results.extend(contact.check_contact(parsed))
    results.extend(sections.check_sections(parsed))
    results.append(structure.check_date_completeness(parsed))
    results.append(structure.check_employment_gaps(parsed))
    results.append(structure.check_bullet_length(bullets))
    results.append(impact.check_action_verbs(bullets))
    results.append(integrity.check_data_integrity(parsed, raw_text or ""))
    return results, bullets


async def _semantic_layer(
    db: AsyncSession,
    version,
    parsed: dict,
    bullets: list[Bullet],
    results: list[CheckResult],
) -> bool:
    """Append the two model-dependent checks. Returns ``semantic_verified``."""
    vocabulary = await resolve_role_vocabulary(db, version.target_role)
    if vocabulary is None:
        results.append(
            skipped(
                "role_keyword_coverage",
                "No expected vocabulary could be built for this target role.",
            )
        )
    else:
        results.append(
            keywords.check_keyword_coverage(
                vocabulary, version.raw_text or "", parsed.get("skills") or []
            )
        )

    judged = bullets[:MAX_BULLETS_FOR_LLM]
    judgment = await judge_semantics(
        version.target_role or "",
        str(parsed.get("summary") or ""),
        judged,
    )
    results.append(_alignment_result(judgment))

    if judgment is not None and judgment.bullet_verdicts:
        results.append(_impact_from_model(judged, judgment))
        return True
    if not judged:
        results.append(_impact_from_regex(judged))
        return True
    results.append(_impact_from_regex(judged))
    return False


async def analyze_cv_version(
    db: AsyncSession,
    user_id: int,
    cv_version_id: UUID | None = None,
    force: bool = False,
) -> ATSReportOut:
    if cv_version_id is None:
        version, error = await find_current_cv_version(db, user_id)
    else:
        version, error = await find_owned_cv_version(db, user_id, cv_version_id)

    if version is None and error == "not_ready":
        raise ATSCVNotReadyError("CV is still processing")
    if version is None:
        raise ATSCVNotFoundError("No completed CV found")
    if not version.parsed_data:
        raise ATSCVNotReadyError("CV has no parsed content yet")

    parsed = dict(version.parsed_data)
    digest = content_hash(version.raw_text, parsed)

    cached = await get_report(db, version.id, digest, RULESET_VERSION)
    if cached is not None and not force and cached.semantic_verified:
        return _report_to_out(cached)

    results, bullets = _run_deterministic(parsed, version.raw_text)
    semantic_verified = await _semantic_layer(db, version, parsed, bullets, results)

    pdf_bytes = await asyncio.to_thread(_download_source_pdf, version.s3_key)
    results.extend(parsability.check_parsability(pdf_bytes))

    results.sort(key=check_sort_key)
    score, insights = aggregate(results)

    if cached is not None:
        await delete_report(db, version.id, digest, RULESET_VERSION)

    report = ATSReport(
        user_id=user_id,
        cv_version_id=version.id,
        score=score,
        checks=[_check_payload(result) for result in results],
        summary=[insight.model_dump() for insight in insights],
        semantic_verified=semantic_verified,
        content_hash=digest,
        ruleset_version=RULESET_VERSION,
    )
    db.add(report)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        winner = await get_report(db, version.id, digest, RULESET_VERSION)
        if winner is None:
            raise
        return _report_to_out(winner)

    await db.refresh(report)
    return _report_to_out(report)


def _report_to_out(report: ATSReport) -> ATSReportOut:
    return ATSReportOut(
        id=report.id,
        cv_version_id=report.cv_version_id,
        score=report.score,
        insights=[InsightOut(**item) for item in (report.summary or [])],
        checks=[CheckOut(**item) for item in (report.checks or [])],
        semantic_verified=report.semantic_verified,
        content_hash=report.content_hash,
        ruleset_version=report.ruleset_version,
        created_at=report.created_at,
    )


def _list_item(report: ATSReport) -> ATSReportListItem:
    return ATSReportListItem(
        id=report.id,
        cv_version_id=report.cv_version_id,
        score=report.score,
        semantic_verified=report.semantic_verified,
        created_at=report.created_at,
    )


async def list_reports(
    db: AsyncSession,
    user_id: int,
    cv_version_id: UUID | None,
    limit: int,
    offset: int,
) -> ATSReportListOut:
    total, rows = await query_reports(db, user_id, cv_version_id, limit, offset)
    return ATSReportListOut(total=total, items=[_list_item(row) for row in rows])


async def get_report_out(
    db: AsyncSession, report_id: UUID, user_id: int
) -> ATSReportOut | None:
    report = await get_report_owned(db, report_id, user_id)
    if report is None:
        return None
    return _report_to_out(report)
