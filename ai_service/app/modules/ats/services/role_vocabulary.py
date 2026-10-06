"""Expand a short ``target_role`` string into the vocabulary a role expects.

``target_role`` is a job title, not a profile -- "Backend Engineer" says nothing
about what a CV must mention.  This turns it into an explicit term list so the
coverage check can stay a pure set intersection instead of asking a model to
score relevance on every request.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.llm_client import get_structured_llm
from app.modules.ats.repository import (
    get_role_vocabulary as fetch_role_vocabulary,
)
from app.modules.ats.repository import save_role_vocabulary

logger = logging.getLogger(__name__)

_SYSTEM = """You are building the keyword checklist a resume must satisfy to be
considered qualified for one specific target role.

Return 20 to 40 terms. A term is a concrete skill, tool, platform, method or
domain noun that a recruiter or an applicant tracking system would look for when
screening for this role.

Include:
* the technologies and tools this role is expected to use day to day
* the methods and practices it is expected to know
* the domain nouns that appear in its job descriptions

Exclude:
* seniority adjectives (junior, senior, lead, principal)
* generic soft skills (communication, teamwork, leadership, passionate)
* anything derived from the candidate's CV rather than the role
* full sentences or phrases longer than four words

Term casing is irrelevant; the caller matches case-insensitively."""


class RoleVocabularyOutput(BaseModel):
    terms: list[str] = Field(min_length=5, max_length=60)


def normalize_role(role: str | None) -> str:
    return " ".join((role or "").split()).lower()


async def resolve_role_vocabulary(db: AsyncSession, target_role: str | None) -> list[str] | None:
    """Expected terms for the role, or ``None`` when no vocabulary is available.

    A cache miss costs one model call and is stored per role. Any failure --
    model, timeout, malformed output, duplicate insert from a concurrent request
    -- degrades to ``None`` so keyword scoring skips rather than guessing.
    """
    normalized = normalize_role(target_role)
    if not normalized:
        return None

    cached = await fetch_role_vocabulary(db, normalized)
    if cached is not None:
        return [str(term) for term in cached.terms]

    try:
        llm = get_structured_llm(RoleVocabularyOutput)
        result = await llm.ainvoke(
            [
                SystemMessage(content=_SYSTEM),
                HumanMessage(content=f"Target role: {target_role}"),
            ]
        )
        parsed = RoleVocabularyOutput.model_validate(result)
        terms = sorted({term.strip() for term in parsed.terms if term.strip()})
    except Exception as exc:
        logger.warning("Role vocabulary expansion failed for %r: %s", target_role, exc)
        return None

    if not terms:
        return None

    try:
        await save_role_vocabulary(
            db,
            role=target_role or normalized,
            normalized_role=normalized,
            terms=terms,
            model_name=settings.OPENROUTER_MODEL,
        )
    except IntegrityError:
        await db.rollback()
        cached = await fetch_role_vocabulary(db, normalized)
        if cached is not None:
            return [str(term) for term in cached.terms]
        return None

    return terms
