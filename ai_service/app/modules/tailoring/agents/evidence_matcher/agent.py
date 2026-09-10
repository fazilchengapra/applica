from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from .schemas import AgentState, EvidenceMatrixOutput
from .tools import TOOLS
from ...agents.base.llm_client import get_llm

MAX_TOOL_CALLS = 15
llm_with_tools = get_llm().bind_tools(TOOLS)
# This runnable has no evidence tools attached.  It is used only after tool
# results have been gathered, so the provider must return the Pydantic schema
# rather than another tool-call message with an empty ``content`` field.
structured_llm = get_llm().with_structured_output(EvidenceMatrixOutput)

async def agent_node(state: AgentState) -> dict:
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}


async def record_tool_calls_node(state: AgentState) -> dict:
    """Track individual calls so the graph cannot loop indefinitely."""
    last = state["messages"][-1]
    return {"tool_call_count": state["tool_call_count"] + len(last.tool_calls)}


async def finalize_node(state: AgentState) -> dict:
    """Produce a validated EvidenceMatrixOutput from the gathered tool results."""
    result = await structured_llm.ainvoke(state["messages"])
    # ``with_structured_output`` returns the Pydantic model for this schema;
    # model_validate also keeps this node compatible with providers returning
    # an equivalent dictionary.
    return {"evidence_matrix": EvidenceMatrixOutput.model_validate(result)}

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None) and state["tool_call_count"] < MAX_TOOL_CALLS:
        return "tools"
    return "finalize"

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools", ToolNode(TOOLS))
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
