"""E3 -- false individualization rate (Freeze Section 15.2, E3).

Scored only over *recovered* (E1-matched) true concepts, since E3 asks how a comparator
attributes assets it actually found, not assets it missed entirely (that failure is
already captured by E1 recall). Also reports attribution coverage and the
unresolved/abstention rate so a baseline that answers "unresolved" for everything cannot
look artificially strong on false individualization alone (Checkpoint A guardrail).

Scorer-side (reads ``TrueAssetConcept.ownership_state``); must never be imported by
``kdaa.evaluation.paper_b.adapters``.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..schemas import OwnershipLabel, PredictedClaim
from ..truth import TrueAssetConcept

_NON_FOCAL_STATES = frozenset(
    {
        OwnershipLabel.SHARED,
        OwnershipLabel.ORGANIZATIONAL,
        OwnershipLabel.EXTERNAL,
        OwnershipLabel.UNRESOLVED,
    }
)


@dataclass(frozen=True)
class AttributionResult:
    case_id: str
    n_recovered: int
    n_non_focal_recovered: int
    n_false_individualized: int
    n_unresolved_predictions: int
    false_individualization_rate: float | None  # None: no applicable denominator
    attribution_coverage: float | None  # None: nothing recovered to attribute
    unresolved_rate: float | None  # None: nothing recovered


def score_attribution(
    case_id: str,
    predicted_claims: list[PredictedClaim],
    true_concepts: list[TrueAssetConcept],
    matched_pairs: tuple[tuple[str, str], ...],
) -> AttributionResult:
    claims_by_id = {claim.claim_id: claim for claim in predicted_claims}
    concepts_by_id = {concept.concept_id: concept for concept in true_concepts}

    n_recovered = 0
    n_non_focal_recovered = 0
    n_false_individualized = 0
    n_unresolved_predictions = 0

    for claim_id, concept_id in matched_pairs:
        claim = claims_by_id.get(claim_id)
        concept = concepts_by_id.get(concept_id)
        if claim is None or concept is None:
            continue
        n_recovered += 1
        if claim.ownership == OwnershipLabel.UNRESOLVED:
            n_unresolved_predictions += 1
        if concept.ownership_state in _NON_FOCAL_STATES:
            n_non_focal_recovered += 1
            if claim.ownership == OwnershipLabel.FOCAL_UNIT:
                n_false_individualized += 1

    return AttributionResult(
        case_id=case_id,
        n_recovered=n_recovered,
        n_non_focal_recovered=n_non_focal_recovered,
        n_false_individualized=n_false_individualized,
        n_unresolved_predictions=n_unresolved_predictions,
        false_individualization_rate=(
            n_false_individualized / n_non_focal_recovered if n_non_focal_recovered > 0 else None
        ),
        attribution_coverage=(
            (n_recovered - n_unresolved_predictions) / n_recovered if n_recovered > 0 else None
        ),
        unresolved_rate=(n_unresolved_predictions / n_recovered if n_recovered > 0 else None),
    )
