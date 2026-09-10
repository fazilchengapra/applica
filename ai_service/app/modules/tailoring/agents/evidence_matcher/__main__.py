import asyncio
from langchain_core.messages import SystemMessage, HumanMessage
from .agent import evidence_matcher_graph
from .prompts import SYSTEM_PROMPT

async def main():
    initial_state = {
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content="Job requirements: [\"3+ years Django\", \"AWS SNS/SQS experience\", \"pgvector or vector DB experience\"]. Evaluate candidate user_id=21."),
        ],
        "user_id": 21,
        "job_id": "55287da3-d44e-41ad-8a4e-bc334eae4e43",
        "tool_call_count": 0,
        "evidence_matrix": None,
    }
    result = await evidence_matcher_graph.ainvoke(initial_state)
    print(result["evidence_matrix"].model_dump_json(indent=2))

if __name__ == "__main__":
    asyncio.run(main())
