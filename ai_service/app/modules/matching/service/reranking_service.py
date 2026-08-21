from app.core.llm_client import get_structured_llm
from pydantic import BaseModel


class MatchEvaluation(BaseModel):
    relevance_score: float  # 0-1
    reasoning: str
    key_matches: list[str]
    key_gaps: list[str]


async def rerank_with_llm(cv_text: str, job_chunks: list[str]) -> MatchEvaluation:
    llm = get_structured_llm(MatchEvaluation)
    prompt = (
        f"CV:\n{cv_text}\n\nJob excerpts:\n{chr(10).join(job_chunks)}\n\nEvaluate fit."
    )
    return await llm.ainvoke(prompt)
