from typing import Literal

from pydantic import BaseModel, Field


class StrategyBrief(BaseModel):
    lead_experiences: list[str] = Field(
        ..., description="chunk_ids from the evidence matrix to foreground, ordered by relevance"
    )
    gaps_to_address: list[str] = Field(
        ..., description="requirement texts marked not_met or partial that the writer should "
                          "acknowledge or reframe carefully — never fabricate evidence for these"
    )
    keywords_to_weave: list[str] = Field(
        ..., description="ATS keywords drawn from the job's own requirement text"
    )
    section_order: list[str] = Field(
        ..., description="ordered CV section names, e.g. ['summary', 'skills', 'experience', 'education']"
    )
    tone: Literal["formal", "conversational", "technical", "executive"] = Field(
        description="Writing tone that best fits the target role."
    )
    reasoning: str = Field(..., description="brief internal rationale, not shown to the candidate")
