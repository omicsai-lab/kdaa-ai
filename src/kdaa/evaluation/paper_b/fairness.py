"""Fairness validation for Paper B comparator predictions (Freeze Section 12).

Confirms that any observed difference between two comparators' predictions comes from
system design, not from one comparator receiving different, better-ordered, or
better-repaired input than the other.
"""

from __future__ import annotations

from .schemas import InputSnapshot, PredictionBundle

MAX_CAPABILITY_PREDICTIONS = 10
REQUIRED_RANKED_OPPORTUNITIES = 10


class FairnessError(RuntimeError):
    """Raised when a comparator's input or output violates the fairness contract."""


def assert_same_input(snapshot_a: InputSnapshot, snapshot_b: InputSnapshot) -> None:
    """Both comparators must receive identical case boundary, evidence content, evidence
    order, and opportunity candidate set."""
    if snapshot_a.case_id != snapshot_b.case_id:
        raise FairnessError(
            f"Case ID mismatch between comparator inputs: {snapshot_a.case_id!r} != {snapshot_b.case_id!r}"
        )
    if snapshot_a.traces != snapshot_b.traces:
        raise FairnessError(f"Evidence content/order differs for case {snapshot_a.case_id}")
    if snapshot_a.opportunity_catalog != snapshot_b.opportunity_catalog:
        raise FairnessError(f"Opportunity candidate set differs for case {snapshot_a.case_id}")


def assert_within_output_limits(prediction: PredictionBundle, snapshot: InputSnapshot) -> None:
    """A comparator's own output must not exceed the frozen fairness caps (experiment_lock:
    fairness.max_asset_candidates=10, fairness.max_ranked_opportunities=10) and must rank
    exactly the case's own opportunity catalog -- no more, no fewer, no substitutions.
    """
    if len(prediction.claims) > MAX_CAPABILITY_PREDICTIONS:
        raise FairnessError(
            f"{prediction.comparator_id} returned {len(prediction.claims)} capability "
            f"predictions for case {prediction.case_id}, exceeding the cap of "
            f"{MAX_CAPABILITY_PREDICTIONS}"
        )
    if not prediction.ranked_opportunities:
        return  # a comparator may abstain from ranking; E4 handles this explicitly.
    predicted_ids = [item.opportunity_id for item in prediction.ranked_opportunities]
    catalog_ids = {candidate.opportunity_id for candidate in snapshot.opportunity_catalog}
    if len(predicted_ids) != REQUIRED_RANKED_OPPORTUNITIES:
        raise FairnessError(
            f"{prediction.comparator_id} ranked {len(predicted_ids)} opportunities for case "
            f"{prediction.case_id}, expected exactly {REQUIRED_RANKED_OPPORTUNITIES}"
        )
    if set(predicted_ids) != catalog_ids:
        raise FairnessError(
            f"{prediction.comparator_id} ranked a different opportunity ID set than the case "
            f"catalog for case {prediction.case_id}"
        )
    if len(set(predicted_ids)) != len(predicted_ids):
        raise FairnessError(
            f"{prediction.comparator_id} ranked a duplicate opportunity ID for case {prediction.case_id}"
        )


def validate_case_fairness(
    snapshot_a: InputSnapshot,
    prediction_a: PredictionBundle,
    snapshot_b: InputSnapshot,
    prediction_b: PredictionBundle,
) -> None:
    """Full fairness check for one case's pair of comparator predictions."""
    assert_same_input(snapshot_a, snapshot_b)
    assert_within_output_limits(prediction_a, snapshot_a)
    assert_within_output_limits(prediction_b, snapshot_b)
