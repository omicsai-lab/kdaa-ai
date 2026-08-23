from datetime import date

from kdaa.evaluation.paper_b.adapters.c4_hybrid import run_c4
from kdaa.evaluation.paper_b.adapters.fake_provider import FakeJSONProvider
from kdaa.evaluation.paper_b.dev_cases import generate_development_case
from kdaa.evaluation.paper_b.schemas import OwnershipLabel
from kdaa.evaluation.paper_b.snapshot import build_snapshot_for_case
from kdaa.evaluation.paper_b.telemetry import AttemptStatus
from kdaa.ontology import Ontology

_AS_OF_DATE = date(2026, 6, 1)
_VALID_RESPONSE = {
    "concepts": [{"label": "Agentic AI", "evidence_ids": []}],
    "ranked_opportunity_ids": [],
}


def test_c4_returns_success_attempt_with_prediction_using_fake_provider() -> None:
    ontology = Ontology.default()
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    provider = FakeJSONProvider([_VALID_RESPONSE])

    attempt = run_c4(case.evidence_bundle, snapshot, ontology, provider, as_of_date=_AS_OF_DATE)
    assert attempt.status == AttemptStatus.SUCCESS
    assert attempt.prediction is not None
    assert attempt.comparator_id == "C4"
    assert len(attempt.prediction.claims) <= 10
    catalog_ids = {c.opportunity_id for c in snapshot.opportunity_catalog}
    ranked_ids = {o.opportunity_id for o in attempt.prediction.ranked_opportunities}
    assert ranked_ids == catalog_ids


def test_c4_preserves_conservative_unresolved_ownership_default() -> None:
    # WP2's conservative default (no ownership-inference rule exists) must be preserved
    # unchanged -- C4 must not add ownership inference merely to improve E3.
    ontology = Ontology.default()
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    provider = FakeJSONProvider([_VALID_RESPONSE])

    attempt = run_c4(case.evidence_bundle, snapshot, ontology, provider, as_of_date=_AS_OF_DATE)
    assert attempt.prediction is not None
    # C4's claims come from the real KDAA pipeline (deterministic assets merged with any
    # LLM-suggested ones); both currently default ownership_state to UNRESOLVED.
    assert all(claim.ownership == OwnershipLabel.UNRESOLVED for claim in attempt.prediction.claims)


def test_c4_retries_on_provider_failure_and_eventually_succeeds() -> None:
    import httpx

    ontology = Ontology.default()
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    provider = FakeJSONProvider([httpx.TimeoutException("slow"), _VALID_RESPONSE])

    attempt = run_c4(case.evidence_bundle, snapshot, ontology, provider, as_of_date=_AS_OF_DATE)
    assert attempt.status == AttemptStatus.SUCCESS
    assert provider.call_count == 2


def test_c4_records_failure_without_crashing_when_provider_always_fails() -> None:
    ontology = Ontology.default()
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)
    provider = FakeJSONProvider([ValueError("bad")] * 5)

    attempt = run_c4(case.evidence_bundle, snapshot, ontology, provider, as_of_date=_AS_OF_DATE)
    assert attempt.status != AttemptStatus.SUCCESS
    assert attempt.prediction is None
    assert attempt.error_message


def test_c4_uses_the_unmodified_production_hybrid_pipeline() -> None:
    # Structural guard: run_c4's own source calls KDAAPipeline with mode="hybrid" and
    # never constructs its own discovery/assessment logic.
    import ast
    import inspect

    from kdaa.evaluation.paper_b.adapters import c4_hybrid

    source = inspect.getsource(c4_hybrid.run_c4)
    assert "KDAAPipeline" in source
    tree = ast.parse(source)
    string_constants = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
    assert "hybrid" in string_constants
