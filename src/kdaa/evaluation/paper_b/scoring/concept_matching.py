"""E1 -- asset-concept precision/recall/F1 (Freeze Section 15.2, E1).

One-to-one matching via true maximum-weight bipartite assignment
(``scipy.optimize.linear_sum_assignment``), so one broad prediction can never be counted
against more than one true concept (Checkpoint A requirement).

This module reads truth (``TrueAssetConcept``) and is therefore scorer-side code, not
inference-side: it must never be imported by anything under
``kdaa.evaluation.paper_b.adapters`` (see ``kdaa.evaluation.paper_b.boundary``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from scipy.optimize import linear_sum_assignment

from kdaa.ontology import normalize_text

from ..schemas import PredictedClaim
from ..truth import TrueAssetConcept

DEFAULT_SEMANTIC_THRESHOLD = 0.5


class SemanticEvaluator(Protocol):
    def similarity(self, text_a: str, text_b: str) -> float:
        """Return a similarity score in [0, 1]; higher means more similar."""
        ...


@dataclass(frozen=True)
class ConceptMatchResult:
    case_id: str
    precision: float
    recall: float
    f1: float
    exact_or_alias_matches: int
    semantic_only_matches: int
    n_predicted: int
    n_true: int
    matched_pairs: tuple[tuple[str, str], ...]  # (claim_id, concept_id)


def _contains_normalized(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    pattern = rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])"
    return re.search(pattern, haystack) is not None


def _exact_or_alias_match(predicted_label: str, true_concept: TrueAssetConcept) -> bool:
    normalized_predicted = normalize_text(predicted_label)
    candidates = [true_concept.canonical_label, *true_concept.aliases]
    return any(
        _contains_normalized(normalized_predicted, normalize_text(candidate))
        for candidate in candidates
        if candidate
    )


def score_concepts(
    case_id: str,
    predicted_claims: list[PredictedClaim],
    true_concepts: list[TrueAssetConcept],
    *,
    semantic_evaluator: SemanticEvaluator | None = None,
    semantic_threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
) -> ConceptMatchResult:
    n_predicted = len(predicted_claims)
    n_true = len(true_concepts)
    if n_predicted == 0 or n_true == 0:
        f1 = 1.0 if n_predicted == 0 and n_true == 0 else 0.0
        return ConceptMatchResult(
            case_id=case_id,
            precision=0.0,
            recall=0.0,
            f1=f1,
            exact_or_alias_matches=0,
            semantic_only_matches=0,
            n_predicted=n_predicted,
            n_true=n_true,
            matched_pairs=(),
        )

    weight = [[0.0] * n_true for _ in range(n_predicted)]
    is_exact = [[False] * n_true for _ in range(n_predicted)]
    for i, claim in enumerate(predicted_claims):
        for j, concept in enumerate(true_concepts):
            if _exact_or_alias_match(claim.label, concept):
                weight[i][j] = 1.0
                is_exact[i][j] = True
            elif semantic_evaluator is not None:
                score = semantic_evaluator.similarity(claim.label, concept.canonical_label)
                if score >= semantic_threshold:
                    weight[i][j] = score

    cost = [[-w for w in row] for row in weight]
    row_ind, col_ind = linear_sum_assignment(cost)

    matched_pairs: list[tuple[str, str]] = []
    exact_or_alias_matches = 0
    semantic_only_matches = 0
    for i, j in zip(row_ind, col_ind, strict=True):
        if weight[i][j] <= 0.0:
            continue
        matched_pairs.append((predicted_claims[i].claim_id, true_concepts[j].concept_id))
        if is_exact[i][j]:
            exact_or_alias_matches += 1
        else:
            semantic_only_matches += 1

    true_positives = len(matched_pairs)
    precision = true_positives / n_predicted
    recall = true_positives / n_true
    f1 = 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)

    return ConceptMatchResult(
        case_id=case_id,
        precision=precision,
        recall=recall,
        f1=f1,
        exact_or_alias_matches=exact_or_alias_matches,
        semantic_only_matches=semantic_only_matches,
        n_predicted=n_predicted,
        n_true=n_true,
        matched_pairs=tuple(matched_pairs),
    )
