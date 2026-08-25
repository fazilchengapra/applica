from app.core.llm_client import get_structured_llm
from app.modules.matching.schemas.match_evaluation import MatchEvaluation


async def rerank_with_llm(cv_text: str, job_chunks: list[str]) -> MatchEvaluation:
    llm = get_structured_llm(MatchEvaluation)
    prompt = (
        f"CV:\n{cv_text}\n\nJob excerpts:\n{chr(10).join(job_chunks)}\n\nEvaluate fit."
    )
    return await llm.ainvoke(prompt)
