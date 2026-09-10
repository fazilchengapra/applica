import asyncio
import json
from .agent import run_strategist

# Paste a real evidence matrix output from your evidence matcher test run here
SAMPLE_EVIDENCE_MATRIX = {
    "items": [
        {"requirement": "3+ years Django", "status": "met", "confidence": 0.92,
         "evidence_chunk_ids": ["chunk_012"], "excerpt": "4 years building Django REST APIs...",
         "reasoning": "Explicit years and framework match."},
        {"requirement": "Kubernetes experience", "status": "not_met", "confidence": 0.05,
         "evidence_chunk_ids": [], "excerpt": "", "reasoning": "No mention in any retrieved chunk."},
    ]
}
SAMPLE_JOB_REQUIREMENTS = [
    {"text": "3+ years Django", "required": True, "weight": 0.9},
    {"text": "Kubernetes experience", "required": False, "weight": 0.4},
]
SAMPLE_CANDIDATE_METADATA = {"years_experience": 4, "education": "BSc Computer Science"}


async def main():
    brief = await run_strategist(SAMPLE_EVIDENCE_MATRIX, SAMPLE_JOB_REQUIREMENTS, SAMPLE_CANDIDATE_METADATA)
    print(brief.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())