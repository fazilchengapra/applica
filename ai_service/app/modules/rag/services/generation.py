"""Generate a grounded final answer from the retrieved chunks."""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions about the organisation's "
    "documents. Answer ONLY from the context provided. If the context does not "
    "contain the answer, say so rather than guessing. Be concise and factual."
)


def _answer_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
        temperature=0,
        max_tokens=512,
    )


async def generate_answer(query: str, context: str) -> str:
    """Answer ``query`` using only the retrieved ``context``."""
    if not context.strip():
        return "I could not find any relevant information to answer that question."

    user_prompt = (
        f"Question:\n{query}\n\n"
        f"Context:\n{context}\n\n"
        "Answer the question based ONLY on the context above."
    )
    result = await _answer_llm().ainvoke(
        [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
    )
    return result.content if result.content is not None else ""