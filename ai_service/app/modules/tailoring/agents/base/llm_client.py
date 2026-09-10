from langchain_openai import ChatOpenAI
from app.core.config import settings


def get_llm(model: str = "openai/gpt-4o-mini"):
    return ChatOpenAI(
        model=model,
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
        temperature=0,
    )
