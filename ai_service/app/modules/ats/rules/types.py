"""Shared value types for the pure rule functions in this package."""

from dataclasses import dataclass, field

from app.modules.ats.constants import CHECKS_BY_ID, CheckStatus


@dataclass(frozen=True)
class CheckResult:
    id: str
    status: CheckStatus
    score: float
    value: str
    detail: str = ""
    evidence: dict = field(default_factory=dict)

    @property
    def category(self) -> str:
        return CHECKS_BY_ID[self.id].category

    @property
    def weight(self) -> int:
        return CHECKS_BY_ID[self.id].weight


def skipped(check_id: str, reason: str) -> CheckResult:
    return CheckResult(
        id=check_id,
        status=CheckStatus.SKIPPED,
        score=0.0,
        value="Not checked",
        detail=reason,
    )
