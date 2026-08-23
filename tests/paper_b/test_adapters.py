from datetime import date

from kdaa.evaluation.paper_b.adapters.c0_semantic import run_c0_s
from kdaa.evaluation.paper_b.adapters.c3_deterministic import run_c3
from kdaa.evaluation.paper_b.adapters.embeddings import FakeEmbeddingBackend
from kdaa.evaluation.paper_b.dev_cases import generate_development_case
from kdaa.evaluation.paper_b.schemas import OwnershipLabel
from kdaa.evaluation.paper_b.snapshot import build_snapshot_for_case
from kdaa.ontology import Ontology

_AS_OF_DATE = date(2026, 6, 1)


def test_c0_s_returns_at_most_ten_claims_and_ranks_the_full_catalog() -> None:
    ontology = Ontology.default()
    case = generate_development_case(1)
    snapshot = build_snapshot_for_case(case)
    prediction = run_c0_s(snapshot, ontology, embedding_backend=FakeEmbeddingBackend())
    assert len(prediction.claims) <= 10
    assert prediction.comparator_id == "C0-S"
    catalog_ids = {c.opportunity_id for c in snapshot.opportunity_catalog}
    ranked_ids = [o.opportunity_id for o in prediction.ranked_opportunities]
    assert set(ranked_ids) == catalog_ids
    assert len(ranked_ids) == 10


def test_c0_s_always_predicts_unresolved_ownership() -> None:
    ontology = Ontology.default()
    case = generate_development_case(2)
    snapshot = build_snapshot_for_case(case)
    prediction = run_c0_s(snapshot, ontology, embedding_backend=FakeEmbeddingBackend())
    assert all(claim.ownership == OwnershipLabel.UNRESOLVED for claim in prediction.claims)


def test_c0_s_is_deterministic_for_fixed_input() -> None:
    ontology = Ontology.default()
    case = generate_development_case(3)
    snapshot = build_snapshot_for_case(case)
    first = run_c0_s(snapshot, ontology, embedding_backend=FakeEmbeddingBackend())
    second = run_c0_s(snapshot, ontology, embedding_backend=FakeEmbeddingBackend())
    assert [c.label for c in first.claims] == [c.label for c in second.claims]
    assert [o.opportunity_id for o in first.ranked_opportunities] == [
        o.opportunity_id for o in second.ranked_opportunities
    ]


def test_c3_returns_at_most_ten_claims_and_ranks_the_full_catalog() -> None:
    ontology = Ontology.default()
    case = generate_development_case(1)
    snapshot = build_snapshot_for_case(case)
    prediction = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=_AS_OF_DATE)
    assert len(prediction.claims) <= 10
    assert prediction.comparator_id == "C3"
    catalog_ids = {c.opportunity_id for c in snapshot.opportunity_catalog}
    ranked_ids = [o.opportunity_id for o in prediction.ranked_opportunities]
    assert set(ranked_ids) == catalog_ids
    assert len(ranked_ids) == 10


def test_c3_reuses_the_unmodified_production_pipeline_ownership_default() -> None:
    # C3's claims reflect whatever the real KDAA pipeline produced -- currently always
    # UNRESOLVED (WP2 conservative default; no ownership-inference rule exists yet). This
    # test documents that as the adapter's honest passthrough, not a bug in the adapter.
    ontology = Ontology.default()
    case = generate_development_case(1)
    snapshot = build_snapshot_for_case(case)
    prediction = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=_AS_OF_DATE)
    assert prediction.claims
    assert all(claim.ownership == OwnershipLabel.UNRESOLVED for claim in prediction.claims)


def test_c3_is_deterministic_for_fixed_as_of_date() -> None:
    ontology = Ontology.default()
    case = generate_development_case(4)
    snapshot = build_snapshot_for_case(case)
    first = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=_AS_OF_DATE)
    second = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=_AS_OF_DATE)
    assert [c.claim_id for c in first.claims] == [c.claim_id for c in second.claims]
    assert [o.opportunity_id for o in first.ranked_opportunities] == [
        o.opportunity_id for o in second.ranked_opportunities
    ]
