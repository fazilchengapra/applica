from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

class EvidenceMatrixItem(BaseModel):
    requirement: str = Field(description="The job requirement being evaluated.")
    status: Literal["met", "partial", "not_met"] = Field(
        description="Whether the retrieved CV evidence satisfies the requirement."
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in the evidence assessment, from 0 to 1.",
    )
    evidence_chunk_ids: list[str] = Field(
        description="IDs of retrieved CV chunks that support this assessment."
    )
    excerpt: str = Field(
        description="A short excerpt from the cited chunks, or an empty string if none exists."
    )
    reasoning: str = Field(description="A concise, evidence-grounded explanation.")

class EvidenceMatrixOutput(BaseModel):
    items: list[EvidenceMatrixItem] = Field(
        description="One evidence assessment for every job requirement."
    )

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    user_id: int
    job_id: str
    tool_call_count: int
    evidence_matrix: EvidenceMatrixOutput | None
