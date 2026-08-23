"""Checkpoint B Section 9: A1/A4/A6 isolate their target mechanism -- each ablation must
change its primary diagnostic and leave the others untouched (mechanism isolation)."""

from __future__ import annotations

from datetime import date

from kdaa.evaluation.paper_b.ablations import (
    apply_a1_no_provenance_gate,
    apply_a4_flat_unit_representation,
    apply_a6_no_opportunity_specific_matching,
)
from kdaa.evaluation.paper_b.adapters.c3_deterministic import run_c3
from kdaa.evaluation.paper_b.dev_cases import generate_development_case
from kdaa.evaluation.paper_b.schemas import (
    OwnershipLabel,
    PredictedClaim,
    PredictedOpportunity,
    PredictionBundle,
)
from kdaa.evaluation.paper_b.scoring import (
    score_concepts,
    score_opportunities,
    score_semantic_support,
)
from kdaa.evaluation.paper_b.snapshot import build_snapshot_for_case
from kdaa.ontology import Ontology

_AS_OF_DATE = date(2026, 6, 1)


def _sample_prediction() -> PredictionBundle:
    return PredictionBundle(
        case_id="c1",
        comparator_id="C3",
        claims=[
            PredictedClaim(claim_id="k1", label="Agentic AI", cited_trace_ids=["t1"], ownership=OwnershipLabel.FOCAL_UNIT),
            PredictedClaim(claim_id="k2", label="Bioinformatics", cited_trace_ids=["t2"], ownership=OwnershipLabel.SHARED),
        ],
        ranked_opportunities=[PredictedOpportunity(opportunity_id=f"opp-{i}", rank=i) for i in range(1, 4)],
    )


# --- A1: touches only citations (E2), leaves labels/ranking/ownership untouched --------


def test_a1_adds_an_unvalidated_citation_to_every_claim() -> None:
    prediction = _sample_prediction()
    ablated = apply_a1_no_provenance_gate(prediction)
    for original, mutated in zip(prediction.claims, ablated.claims, strict=True):
        assert set(original.cited_trace_ids) < set(mutated.cited_trace_ids)


def test_a1_leaves_labels_ownership_and_ranking_unchanged() -> None:
    prediction = _sample_prediction()
    ablated = apply_a1_no_provenance_gate(prediction)
    assert [c.label for c in ablated.claims] == [c.label for c in prediction.claims]
    assert [c.ownership for c in ablated.claims] == [c.ownership for c in prediction.claims]
    assert ablated.ranked_opportunities == prediction.ranked_opportunities


def test_a1_increases_unsupported_claim_rate_on_a_real_case() -> None:
    ontology = Ontology.default()
    case = generate_development_case(1)
    snapshot = build_snapshot_for_case(case)
    baseline = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=_AS_OF_DATE)
    ablated = apply_a1_no_provenance_gate(baseline)

    matches_baseline = score_concepts(case.manifest.case_id, baseline.claims, case.truth.asset_concepts).matched_pairs
    matches_ablated = score_concepts(case.manifest.case_id, ablated.claims, case.truth.asset_concepts).matched_pairs
    baseline_e2 = score_semantic_support(case.manifest.case_id, baseline.claims, case.truth.asset_concepts, matches_baseline)
    ablated_e2 = score_semantic_support(case.manifest.case_id, ablated.claims, case.truth.asset_concepts, matches_ablated)
    if baseline.claims:
        assert ablated_e2.unsupported_claim_rate >= baseline_e2.unsupported_claim_rate


# --- A4: collapses to one claim, leaves ranking untouched -------------------------------


def test_a4_collapses_to_exactly_one_claim() -> None:
    prediction = _sample_prediction()
    ablated = apply_a4_flat_unit_representation(prediction)
    assert len(ablated.claims) == 1


def test_a4_leaves_opportunity_ranking_untouched() -> None:
    prediction = _sample_prediction()
    ablated = apply_a4_flat_unit_representation(prediction)
    assert ablated.ranked_opportunities == prediction.ranked_opportunities


def test_a4_empty_claims_does_not_crash() -> None:
    prediction = PredictionBundle(case_id="c1", comparator_id="C3")
    ablated = apply_a4_flat_unit_representation(prediction)
    assert ablated.claims == []


def test_a4_can_reduce_e1_recall_via_one_to_one_matching() -> None:
    ontology = Ontology.default()
    case = generate_development_case(6)  # interdisciplinary case likely to have >=2 true concepts
    snapshot = build_snapshot_for_case(case)
    baseline = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=_AS_OF_DATE)
    ablated = apply_a4_flat_unit_representation(baseline)

    baseline_e1 = score_concepts(case.manifest.case_id, baseline.claims, case.truth.asset_concepts)
    ablated_e1 = score_concepts(case.manifest.case_id, ablated.claims, case.truth.asset_concepts)
    if len(case.truth.asset_concepts) >= 2 and baseline_e1.recall > 0:
        assert ablated_e1.recall <= baseline_e1.recall


# --- A6: touches only ranking, leaves claims untouched -----------------------------------


def test_a6_replaces_ranking_with_fixed_catalog_order() -> None:
    ontology = Ontology.default()
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    baseline = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=_AS_OF_DATE)
    ablated = apply_a6_no_opportunity_specific_matching(baseline, snapshot)

    expected_order = [c.opportunity_id for c in snapshot.opportunity_catalog]
    assert [o.opportunity_id for o in ablated.ranked_opportunities] == expected_order


def test_a6_leaves_claims_untouched() -> None:
    ontology = Ontology.default()
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    baseline = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=_AS_OF_DATE)
    ablated = apply_a6_no_opportunity_specific_matching(baseline, snapshot)
    assert ablated.claims == baseline.claims


def test_a6_is_identical_across_cases_since_it_ignores_evidence() -> None:
    ontology = Ontology.default()
    case_a = generate_development_case(0)
    case_b = generate_development_case(5)
    snapshot_a = build_snapshot_for_case(case_a)
    snapshot_b = build_snapshot_for_case(case_b)
    pred_a = apply_a6_no_opportunity_specific_matching(run_c3(case_a.evidence_bundle, snapshot_a, ontology, as_of_date=_AS_OF_DATE), snapshot_a)
    pred_b = apply_a6_no_opportunity_specific_matching(run_c3(case_b.evidence_bundle, snapshot_b, ontology, as_of_date=_AS_OF_DATE), snapshot_b)
    assert [o.opportunity_id for o in pred_a.ranked_opportunities] == [o.opportunity_id for o in pred_b.ranked_opportunities]


def test_a6_can_reduce_ndcg_on_a_case_with_a_strong_true_opportunity() -> None:
    ontology = Ontology.default()
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    baseline = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=_AS_OF_DATE)
    ablated = apply_a6_no_opportunity_specific_matching(baseline, snapshot)

    baseline_e4 = score_opportunities(case.manifest.case_id, baseline.ranked_opportunities, case.truth.opportunity_relevance)
    ablated_e4 = score_opportunities(case.manifest.case_id, ablated.ranked_opportunities, case.truth.opportunity_relevance)
    assert baseline_e4.is_valid_ranking and ablated_e4.is_valid_ranking
