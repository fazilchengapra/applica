import json
import logging

from langgraph.graph import StateGraph, END
from langchain_core.messages import ToolMessage

from .schemas import AgentState, EvidenceMatrixOutput
from .tools import TOOLS
from ...agents.base.llm_client import get_llm

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 15
llm_with_tools = get_llm().bind_tools(TOOLS)
structured_llm = get_llm().with_structured_output(EvidenceMatrixOutput)
tools_by_name = {tool.name: tool for tool in TOOLS}


async def agent_node(state: AgentState) -> dict:
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


async def record_tool_calls_node(state: AgentState) -> dict:
    """Track individual calls so the graph cannot loop indefinitely."""
    last = state["messages"][-1]
    return {"tool_call_count": state["tool_call_count"] + len(last.tool_calls)}


async def execute_tools_node(state: AgentState) -> dict:

    last = state["messages"][-1]
    messages = []
    for tool_call in last.tool_calls:
        tool = tools_by_name[tool_call["name"]]
        logger.warning("=" * 80)
        logger.warning("TOOL SELECTED: %s", tool_call["name"])
        logger.warning(
            "TOOL ARGUMENTS: %s", json.dumps(tool_call["args"], indent=2, default=str)
        )
        result = await tool.ainvoke(tool_call["args"])
        messages.append(
            ToolMessage(
                content=json.dumps(result, default=str),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return {"messages": messages}


async def finalize_node(state: AgentState) -> dict:
    """Produce a validated EvidenceMatrixOutput from the gathered tool results."""
    result = await structured_llm.ainvoke(state["messages"])
    return {"evidence_matrix": EvidenceMatrixOutput.model_validate(result)}


def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None) and state["tool_call_count"] < MAX_TOOL_CALLS:
        return "tools"
    return "finalize"


graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", execute_tools_node)
graph.add_node("record_tool_calls", record_tool_calls_node)
graph.add_node("finalize", finalize_node)

graph.set_entry_point("agent")
graph.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "record_tool_calls", "finalize": "finalize"},
)
graph.add_edge("record_tool_calls", "tools")
graph.add_edge("tools", "agent")
graph.add_edge("finalize", END)

evidence_matcher_graph = graph.compile()
