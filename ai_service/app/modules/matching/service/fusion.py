from uuid import UUID


def reciprocal_rank_fusion(
    vector_results: list[tuple[UUID, float]],
    lexical_scores: dict[UUID, float],
    k: int = 60,
):
    vector_ranks = {
        job_id: rank
        for rank, (job_id, _) in enumerate(
            sorted(vector_results, key=lambda x: -x[1]), start=1
        )
    }
    lexical_ranks = {
        job_id: rank
        for rank, job_id in enumerate(
            sorted(lexical_scores, key=lambda j: -lexical_scores[j]), start=1
        )
    }

    all_job_ids = set(vector_ranks) | set(lexical_ranks)
    fused = {}
    for job_id in all_job_ids:
        v_rank = vector_ranks.get(job_id, len(vector_ranks) + 1)
        l_rank = lexical_ranks.get(job_id, len(lexical_ranks) + 1)
        fused[job_id] = 1 / (k + v_rank) + 1 / (k + l_rank)

    return sorted(fused.items(), key=lambda x: -x[1])[:20]  # top 20 for reranking
