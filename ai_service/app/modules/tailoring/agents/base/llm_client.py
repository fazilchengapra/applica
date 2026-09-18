from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek

from app.core.config import settings


def get_llm():
    return ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
        temperature=0,
        max_tokens=4096,
    )


# def get_cv_write_llm():
#     return ChatDeepSeek(
#         model=settings.WRITER_MODEL,
#         base_url=settings.OPENROUTER_BASE_URL,
#         api_key=settings.OPENROUTER_API_KEY,
#         temperature=0,
#         max_tokens=4096,
#     )
