from pydantic import BaseModel
from typing import Literal

class FabricationFlag(BaseModel):
    claim: str
    field: str
    severity: Literal["low", "high"]

class CriticVerdict(BaseModel):
    approved: bool
    fabrication_flags: list[FabricationFlag]
    quality_score: float
    issues: list[str]
    reasoning: str