"""Normalisation and bullet extraction shared by the rule functions."""

import re
from dataclasses import dataclass

from app.modules.ats.constants import CheckStatus
from app.modules.ats.rules.types import CheckResult

_BULLET_PREFIX = re.compile(r"^\s*(?:[-*•◦▪–]|\d{1,2}[.)])\s*")
_WS = re.compile(r"\s+")


def normalize(text: str | None) -> str:
    return _WS.sub(" ", (text or "").strip()).lower()


@dataclass(frozen=True)
class Bullet:
    ref: str
    text: str
    entry_index: int
    bullet_index: int
    is_current: bool


def _split_bullets(description: str) -> list[str]:
    parts = []
    for line in (description or "").splitlines():
        cleaned = _BULLET_PREFIX.sub("", line).strip()
        if cleaned:
            parts.append(cleaned)
    return parts


def collect_bullets(parsed: dict) -> list[Bullet]:
    bullets: list[Bullet] = []
    for entry_index, entry in enumerate(parsed.get("experience") or []):
        if not isinstance(entry, dict):
            continue
        for bullet_index, line in enumerate(_split_bullets(entry.get("description") or "")):
            bullets.append(
                Bullet(
                    ref=f"experience[{entry_index}].bullet[{bullet_index}]",
                    text=line,
                    entry_index=entry_index,
                    bullet_index=bullet_index,
                    is_current=bool(entry.get("is_current")),
                )
            )
    return bullets


def present(check_id: str, value: str, detail: str = "", evidence: dict | None = None) -> CheckResult:
    return CheckResult(
        id=check_id,
        status=CheckStatus.PASS,
        score=1.0,
        value=value,
        detail=detail,
        evidence=evidence or {},
    )


def missing(check_id: str, value: str, detail: str, evidence: dict | None = None) -> CheckResult:
    return CheckResult(
        id=check_id,
        status=CheckStatus.FAIL,
        score=0.0,
        value=value,
        detail=detail,
        evidence=evidence or {},
    )
