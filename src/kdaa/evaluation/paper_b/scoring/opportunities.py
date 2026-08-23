"""E4 -- opportunity-ranking nDCG@5 (Freeze Section 15.2, E4).

Scorer-side (reads ``TrueOpportunityRelevance``); must never be imported by
``kdaa.evaluation.paper_b.adapters``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..schemas import PredictedOpportunity
from ..truth import TrueOpportunityRelevance


@dataclass(frozen=True)
class NdcgResult:
    case_id: str
    ndcg_at_5: float
    is_valid_ranking: bool
    dcg_at_5: float
    idcg_at_5: float


def dcg_at_k(grades: list[int], k: int) -> float:
    """DCG@k = sum(grade_i / log2(i + 2)) for i in [0, k)."""
    return sum(grade / math.log2(index + 2) for index, grade in enumerate(grades[:k]))


def score_opportunities(
    case_id: str,
    ranked_opportunities: list[PredictedOpportunity],
    true_relevance: list[TrueOpportunityRelevance],
    *,
    k: int = 5,
) -> NdcgResult:
    """Score one case's opportunity ranking. A ranking is valid only if it covers exactly
    the same opportunity IDs as truth, with no duplicates -- anything else (an empty
    ranking, a partial ranking, a ranking naming an unknown ID) is an explicit failed run,
    scored ``0.0`` (WP1 experiment lock: ``failure_policy.ndcg_failed_run_value``), not
    silently backfilled from hidden truth.
    """
    relevance_by_id = {item.opportunity_id: item.relevance_grade for item in true_relevance}
    predicted_ids = [item.opportunity_id for item in ranked_opportunities]

    is_valid = (
        len(predicted_ids) == len(relevance_by_id)
        and len(set(predicted_ids)) == len(predicted_ids)
        and set(predicted_ids) == set(relevance_by_id)
    )
    if not is_valid:
        return NdcgResult(
            case_id=case_id, ndcg_at_5=0.0, is_valid_ranking=False, dcg_at_5=0.0, idcg_at_5=0.0
        )

    ranked_grades = [relevance_by_id[opportunity_id] for opportunity_id in predicted_ids]
    ideal_grades = sorted(relevance_by_id.values(), reverse=True)
    dcg = dcg_at_k(ranked_grades, k)
    idcg = dcg_at_k(ideal_grades, k)
    ndcg = 0.0 if idcg == 0.0 else dcg / idcg

    return NdcgResult(case_id=case_id, ndcg_at_5=ndcg, is_valid_ranking=True, dcg_at_5=dcg, idcg_at_5=idcg)
