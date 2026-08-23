import pytest

from kdaa.evaluation.paper_b.dev_cases import generate_development_case
from kdaa.evaluation.paper_b.fairness import (
    FairnessError,
    assert_same_input,
    assert_within_output_limits,
    validate_case_fairness,
)
from kdaa.evaluation.paper_b.schemas import PredictedClaim, PredictedOpportunity, PredictionBundle
from kdaa.evaluation.paper_b.snapshot import build_snapshot_for_case


def _empty_prediction(case_id: str, comparator_id: str) -> PredictionBundle:
    return PredictionBundle(case_id=case_id, comparator_id=comparator_id)


def test_identical_snapshots_pass_fairness() -> None:
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    assert_same_input(snapshot, snapshot)


def test_different_case_ids_fail_fairness() -> None:
    case_a = generate_development_case(0)
    case_b = generate_development_case(1)
    snapshot_a = build_snapshot_for_case(case_a)
    snapshot_b = build_snapshot_for_case(case_b)
    with pytest.raises(FairnessError):
        assert_same_input(snapshot_a, snapshot_b)


def test_reordered_traces_fail_fairness() -> None:
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    reversed_traces = tuple(reversed(snapshot.traces))
    reordered = snapshot.model_copy(update={"traces": reversed_traces})
    with pytest.raises(FairnessError):
        assert_same_input(snapshot, reordered)


def test_more_than_ten_claims_fails_fairness() -> None:
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    claims = [PredictedClaim(claim_id=f"k{i}") for i in range(11)]
    prediction = PredictionBundle(case_id=case.manifest.case_id, comparator_id="test", claims=claims)
    with pytest.raises(FairnessError):
        assert_within_output_limits(prediction, snapshot)


def test_ranking_with_wrong_id_set_fails_fairness() -> None:
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    bad_ranking = [
        PredictedOpportunity(opportunity_id=f"not-real-{i}", rank=i + 1) for i in range(10)
    ]
    prediction = PredictionBundle(
        case_id=case.manifest.case_id, comparator_id="test", ranked_opportunities=bad_ranking
    )
    with pytest.raises(FairnessError):
        assert_within_output_limits(prediction, snapshot)


def test_ranking_with_wrong_count_fails_fairness() -> None:
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    short_ranking = [
        PredictedOpportunity(opportunity_id=c.opportunity_id, rank=i + 1)
        for i, c in enumerate(snapshot.opportunity_catalog[:5])
    ]
    prediction = PredictionBundle(
        case_id=case.manifest.case_id, comparator_id="test", ranked_opportunities=short_ranking
    )
    with pytest.raises(FairnessError):
        assert_within_output_limits(prediction, snapshot)


def test_empty_ranking_is_allowed_as_explicit_abstention() -> None:
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    prediction = _empty_prediction(case.manifest.case_id, "test")
    assert_within_output_limits(prediction, snapshot)  # must not raise


def test_full_case_fairness_passes_for_real_c0s_and_c3_predictions() -> None:
    from datetime import date

    from kdaa.evaluation.paper_b.adapters.c0_semantic import run_c0_s
    from kdaa.evaluation.paper_b.adapters.c3_deterministic import run_c3
    from kdaa.ontology import Ontology

    ontology = Ontology.default()
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    c0s = run_c0_s(snapshot, ontology)
    c3 = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=date(2026, 6, 1))
    validate_case_fairness(snapshot, c0s, snapshot, c3)  # must not raise
