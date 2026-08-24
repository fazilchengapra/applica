from pydantic import BaseModel


class MatchEvaluation(BaseModel):
    relevance_score: float  # 0-1
    reasoning: str
    key_matches: list[str]
    key_gaps: list[str]