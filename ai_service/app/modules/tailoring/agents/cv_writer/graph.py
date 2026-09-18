"""A bounded, auditable LangGraph workflow for tailored CV generation."""

import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from app.modules.tailoring.agents.base.llm_client import get_llm
from app.modules.tailoring.agents.cv_writer.prompts import PROMPT, REVISION_PROMPT
from app.modules.tailoring.agents.cv_writer.schemas import AgentState, CVContent
from app.modules.tailoring.agents.cv_writer.tools import get_cv_metadata

MAX_REVISIONS = 2


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _hydrate_static_sections(content: CVContent, metadata: dict) -> CVContent:
    """Canonical profile data is application-owned, not model-owned."""
    payload = content.model_dump(mode="json")
    payload.update(
        {
            "contact": metadata["contact"],
            "education": metadata.get("education", []),
            "certifications": metadata.get("certifications", []),
        }
    )
    return CVContent.model_validate(payload)


async def fetch_static_cv_data(state: AgentState) -> dict:
    """Load immutable candidate data once; the writer must copy it verbatim."""
    metadata = await get_cv_metadata(
        user_id=state["user_id"], cv_version_id=state["cv_version_id"]
    )
    return {"cv_metadata": metadata.model_dump(mode="json")}


async def write_cv(state: AgentState) -> dict:
    llm = get_llm().with_structured_output(CVContent)
    feedback_block = ""
    if state.get("critic_verdict"):
        feedback_block = (
            "\n\nA previous draft was reviewed and rejected. Here is that exact "
            "draft, followed by the reviewer's issues. Make targeted edits to fix "
            "each addressable issue — do not regenerate unrelated content, and do "
            "not fabricate data to satisfy an issue asking for information not "
            "present in cv_metadata or the evidence matrix:\n\n"
            f"Previous draft:\n{_json(state.get('previous_draft'))}\n\n"
            f"Reviewer issues:\n{_json(state['critic_verdict'].get('issues', []))}"
        )
    result = await llm.ainvoke(
        [
            SystemMessage(content=PROMPT),
            HumanMessage(
                content=(
                    f"cv_metadata:\n{_json(state['cv_metadata'])}\n\n"
                    f"evidence_matrix:\n{state['evidence_matrix'].model_dump_json(indent=2)}\n\n"
                    f"strategy_brief:\n{_json(state['strategy_brief'])}"
                    + feedback_block
                )
            ),
        ],
        config={
            "run_name": "CV Writer LLM",
            "tags": [
                "agent:cv_writer",
                "component:llm",
                "stage:generation",
            ],
        },
    )
    if state.get("critic_verdict"):
        print(state.get("critic_verdict"))
    return {
        "cv_content": _hydrate_static_sections(
            CVContent.model_validate(result), state["cv_metadata"] or {}
        ),
        "validation_errors": [],
    }


def _audit(state: AgentState) -> list[str]:
    """Perform checks that should never be delegated to probabilistic model output."""
    content = state["cv_content"]
    metadata = state["cv_metadata"]
    assert content is not None and metadata is not None

    errors: list[str] = []
    for field in ("contact", "education", "certifications"):
        actual = getattr(content, field)
        actual_value = (
            actual.model_dump(mode="json")
            if hasattr(actual, "model_dump")
            else [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in actual
            ]
        )
        if actual_value != metadata.get(field, [] if field != "contact" else {}):
            errors.append(f"{field} must exactly match cv_metadata.{field}.")

    valid_ids = {
        item.evidence_item_id
        for item in state["evidence_matrix"].items
        if item.evidence_item_id
    }
    if not valid_ids:
        errors.append(
            "Evidence matrix has no persisted evidence_item_ids for traceability."
        )
        return errors

    entries = [*content.experience, *content.projects]
    for index, entry in enumerate(entries):
        unknown = sorted(set(entry.evidence_item_ids) - valid_ids)
        if unknown:
            errors.append(
                f"entry {index} cites unknown evidence_item_ids: {', '.join(unknown)}."
            )
    return errors


async def audit_cv(state: AgentState) -> dict:
    return {"validation_errors": _audit(state)}


def after_audit(state: AgentState) -> Literal["revise", "complete", "failed"]:
    if not state["validation_errors"]:
        return "complete"
    if state["revision_count"] < MAX_REVISIONS:
        return "revise"
    return "failed"


async def revise_cv(state: AgentState) -> dict:
    content = state["cv_content"]
    assert content is not None
    llm = get_llm().with_structured_output(CVContent)
    result = await llm.ainvoke(
        [
            SystemMessage(content=REVISION_PROMPT),
            HumanMessage(
                content=(
                    f"Audit errors:\n{_json(state['validation_errors'])}\n\n"
                    f"cv_metadata:\n{_json(state['cv_metadata'])}\n\n"
                    f"evidence_matrix:\n{state['evidence_matrix'].model_dump_json(indent=2)}\n\n"
                    f"Current document:\n{content.model_dump_json(indent=2)}"
                )
            ),
        ],
        config={
            "run_name": "CV Writer Revision LLM",
            "tags": [
                "agent:cv_writer",
                "component:llm",
                "stage:revision",
            ],
        },
    )
    return {
        "cv_content": _hydrate_static_sections(
            CVContent.model_validate(result), state["cv_metadata"] or {}
        ),
        "revision_count": state["revision_count"] + 1,
    }


async def fail_validation(state: AgentState) -> dict:
    raise ValueError(
        "CV writer could not produce a grounded document after "
        f"{MAX_REVISIONS} revisions: {'; '.join(state['validation_errors'])}"
    )


def build_cv_writer_graph():
    graph = StateGraph(AgentState)
    graph.add_node("fetch_static_cv_data", fetch_static_cv_data)
    graph.add_node("write_cv", write_cv)
    graph.add_node("audit_cv", audit_cv)
    graph.add_node("revise_cv", revise_cv)
    graph.add_node("fail_validation", fail_validation)
    graph.add_edge(START, "fetch_static_cv_data")
    graph.add_edge("fetch_static_cv_data", "write_cv")
    graph.add_edge("write_cv", "audit_cv")
    graph.add_conditional_edges(
        "audit_cv",
        after_audit,
        {"revise": "revise_cv", "complete": END, "failed": "fail_validation"},
    )
    graph.add_edge("revise_cv", "audit_cv")
    graph.add_edge("fail_validation", END)
    return graph.compile()


cv_writer_graph = build_cv_writer_graph()
