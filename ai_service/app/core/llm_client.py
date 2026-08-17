# app/core/llm_client.py  (move here since it's now shared across modules)
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from app.core.config import settings

def get_structured_llm(output_schema: type[BaseModel]) -> ChatOpenAI:
    llm = ChatOpenAI(
        model=settings.OPENROUTER_MODEL,
        base_url=settings.OPENROUTER_BASE_URL,
        api_key=settings.OPENROUTER_API_KEY,
        temperature=0,
    )
    return llm.with_structured_output(output_schema)