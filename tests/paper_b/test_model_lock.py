"""Checkpoint B Section 5: one shared model configuration for C1/C2/C4, no model-shopping."""

from __future__ import annotations

from datetime import date

from kdaa.evaluation.paper_b.adapters.fake_provider import FakeJSONProvider
from kdaa.evaluation.paper_b.dev_cases import generate_development_case
from kdaa.evaluation.paper_b.dev_pilot_llm import run_llm_development_pilot
from kdaa.evaluation.paper_b.telemetry import AttemptStatus
from kdaa.ontology import Ontology

_VALID_RESPONSE = {"concepts": [{"label": "X"}], "ranked_opportunity_ids": []}


def test_pilot_uses_the_same_shared_provider_instance_for_all_three_comparators() -> None:
    ontology = Ontology.default()
    case = generate_development_case(0)
    shared_provider = FakeJSONProvider([_VALID_RESPONSE], model_name="shared-dev-model-v1")

    result = run_llm_development_pilot(
        [case],
        provider_c1=shared_provider,
        provider_c2=shared_provider,
        provider_c4=shared_provider,
        ontology=ontology,
        as_of_date=date(2026, 6, 1),
        n_repeats=1,
    )

    model_identifiers = {
        attempt.resource_usage.model_identifier
        for attempt in result.all_attempts
        if attempt.resource_usage is not None
    }
    assert model_identifiers == {"shared-dev-model-v1"}
    comparators_seen = {attempt.comparator_id for attempt in result.all_attempts}
    assert comparators_seen == {"C1", "C2", "C4"}


def test_pilot_does_not_itself_choose_different_providers_per_comparator() -> None:
    # Structural guard: run_llm_development_pilot's own source never constructs a
    # provider per comparator -- it only ever uses the three provider_* parameters it
    # was given, so model-shopping would have to happen at the call site, visibly.
    import ast
    import inspect

    from kdaa.evaluation.paper_b import dev_pilot_llm

    tree = ast.parse(inspect.getsource(dev_pilot_llm.run_llm_development_pilot))
    calls_constructing_providers = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"OpenAICompatibleProvider", "FakeJSONProvider"}
    ]
    assert calls_constructing_providers == []


def test_all_repeats_within_one_case_use_the_same_provider() -> None:
    ontology = Ontology.default()
    case = generate_development_case(1)
    shared_provider = FakeJSONProvider([_VALID_RESPONSE], model_name="shared-dev-model-v1")

    result = run_llm_development_pilot(
        [case],
        provider_c1=shared_provider,
        provider_c2=shared_provider,
        provider_c4=shared_provider,
        ontology=ontology,
        as_of_date=date(2026, 6, 1),
        n_repeats=3,
    )
    c1_attempts = [a for a in result.all_attempts if a.comparator_id == "C1"]
    assert len(c1_attempts) == 3
    assert all(a.status == AttemptStatus.SUCCESS for a in c1_attempts)
    assert len({a.resource_usage.model_identifier for a in c1_attempts}) == 1
