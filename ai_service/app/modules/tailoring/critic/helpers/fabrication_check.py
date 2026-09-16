"""Deterministic evidence-grounding checks for writer output."""

from dataclasses import dataclass

from app.modules.tailoring.critic.schemas import FabricationFlag


@dataclass(frozen=True)
class Claim:
    text: str
    field: str
    severity: str
    context: str
    evidence_item_ids: list[str]


_HEDGING_LANGUAGE = (
    "exposure to",
    "familiar with",
    "familiarity with",
    "assisted",
    "supported",
    "contributed to",
    "learning",
    "basic understanding",
)


def _context(kind: str, index: int, entry: dict) -> str:
    name = entry.get("company") if kind == "experience" else entry.get("name")
    return f"{kind}[{index}]:{name or 'unnamed'}"


def extract_claims(cv_draft: dict) -> list[Claim]:
    """Flatten the citation-bearing portions of a renderer-ready CV draft."""
    claims: list[Claim] = []
    for kind in ("experience", "projects"):
        for index, entry in enumerate(cv_draft.get(kind, []) or []):
            context = _context(kind, index, entry)
            ids = [str(item) for item in (entry.get("evidence_item_ids") or [])]
            if not ids:
                claims.append(Claim(context, "evidence_ref", "high", context, []))
            else:
                claims.extend(
                    Claim(item_id, "evidence_ref", "high", context, [item_id])
                    for item_id in ids
                )
            claims.extend(
                Claim(bullet, "bullet", "high", context, ids)
                for bullet in (entry.get("bullets") or [])
            )
            claims.extend(
                Claim(technology, "technology", "low", context, ids)
                for technology in (entry.get("technologies") or [])
            )
    claims.extend(
        Claim(skill, "skill", "low", "skills", [])
        for skill in (cv_draft.get("skills") or [])
    )
    return claims


def _relates_to(bullet_text: str, requirement: str, threshold: float = 0.25) -> bool:
    """Loose relevance check — is this bullet plausibly about this requirement?"""
    bullet_words = set(bullet_text.casefold().split())
    req_words = set(requirement.casefold().split())
    if not req_words:
        return False
    overlap = len(bullet_words & req_words) / len(req_words)
    return overlap >= threshold


def is_traceable(
    claim: Claim, evidence_items_by_id: dict[str, dict], gaps_to_address: set[str]
) -> str | None:
    if claim.field == "evidence_ref":
        if not claim.evidence_item_ids:
            return "entry cites no evidence_item_ids"
        if claim.evidence_item_ids[0] not in evidence_items_by_id:
            return f"evidence_item_id {claim.evidence_item_ids[0]!r} does not exist"
        return None

    if claim.field == "bullet":
        cited = [evidence_items_by_id.get(item_id) for item_id in claim.evidence_item_ids]
        if not cited or any(item is None for item in cited):
            missing = [
                item_id
                for item_id in claim.evidence_item_ids
                if item_id not in evidence_items_by_id
            ]
            return f"cited evidence_item_ids do not resolve: {missing}"
        # Heuristic stopgap until the writer has durable per-bullet citations;
        # changing TailoredExperience/TailoredProject bullets to structured
        # objects carrying evidence_item_ids is deliberately out of scope.
        relevant = [
            item
            for item in cited
            if _relates_to(claim.text, str(item.get("requirement") or ""))
        ] or cited
        for item in relevant:
            assert item is not None
            if item.get("status") == "not_met":
                return f"cited evidence for {item.get('requirement')!r} is status=not_met"
            requirement = str(item.get("requirement") or "").casefold()
            if (
                item.get("status") == "partial"
                and requirement in gaps_to_address
                and not any(hedge in claim.text.casefold() for hedge in _HEDGING_LANGUAGE)
            ):
                return (
                    "unqualified claim against partial/gap requirement "
                    f"{item.get('requirement')!r} — needs hedging language"
                )
        return None

    if claim.field in {"technology", "skill"}:
        return None
    return f"unsupported claim field {claim.field!r}"


def check_fabrication(
    cv_draft: dict, evidence_items: list[dict], strategy: dict
) -> list[FabricationFlag]:
    evidence_items_by_id = {str(item["id"]): item for item in evidence_items}
    gaps_to_address = {
        str(requirement).casefold()
        for requirement in (strategy.get("gaps_to_address") or [])
    }
    flags: list[FabricationFlag] = []
    for claim in extract_claims(cv_draft):
        reason = is_traceable(claim, evidence_items_by_id, gaps_to_address)
        if reason is not None:
            flags.append(
                FabricationFlag(
                    claim=claim.text,
                    field=claim.field,
                    severity=claim.severity,
                    context=claim.context,
                    reason=reason,
                )
            )
    return flags
