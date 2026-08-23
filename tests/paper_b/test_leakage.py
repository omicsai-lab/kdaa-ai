import pytest

from kdaa.evaluation.paper_b.dev_cases import generate_development_case
from kdaa.evaluation.paper_b.leakage import (
    LeakageError,
    check_no_metadata_leakage,
    validate_case_leakage,
)
from kdaa.evaluation.paper_b.snapshot import build_snapshot_for_case


def test_real_generated_case_has_no_leakage() -> None:
    case = generate_development_case(0)
    # Must not raise, and must not false-positive on legitimate evidence/concept vocabulary
    # overlap (e.g. a trace titled "...bioinformatics..." supporting a true "bioinformatics"
    # concept is normal data, not a leak).
    snapshot = build_snapshot_for_case(case)
    validate_case_leakage(case.evidence_bundle, case.truth, snapshot)


def test_planted_ground_truth_concepts_key_is_detected() -> None:
    case = generate_development_case(0)
    leaky_bundle = case.evidence_bundle.model_copy(
        update={"metadata": {"ground_truth_concepts": ["agentic_ai"]}}
    )
    with pytest.raises(LeakageError):
        validate_case_leakage(leaky_bundle, case.truth)


def test_planted_true_concept_id_as_metadata_key_is_detected() -> None:
    case = generate_development_case(0)
    concept_id = case.truth.asset_concepts[0].concept_id
    leaky_bundle = case.evidence_bundle.model_copy(update={"metadata": {concept_id: True}})
    with pytest.raises(LeakageError):
        validate_case_leakage(leaky_bundle, case.truth)


def test_planted_hidden_relevance_key_is_detected() -> None:
    case = generate_development_case(0)
    leaky_bundle = case.evidence_bundle.model_copy(
        update={"metadata": {"hidden_relevance": {"opp-repository": 3}}}
    )
    with pytest.raises(LeakageError):
        validate_case_leakage(leaky_bundle, case.truth)


def test_unrelated_metadata_keys_are_not_flagged() -> None:
    case = generate_development_case(0)
    clean_bundle = case.evidence_bundle.model_copy(
        update={"metadata": {"connector": "synthetic", "notes": "development case"}}
    )
    problems = check_no_metadata_leakage(clean_bundle, case.truth)
    assert problems == []


def test_input_snapshot_schema_forbids_extra_fields() -> None:
    # Structural guarantee (WP1 extra="forbid"): confirms there is no field an accidental
    # truth-copy could even be assigned to.
    from pydantic import ValidationError

    from kdaa.evaluation.paper_b.schemas import InputSnapshot

    with pytest.raises(ValidationError):
        InputSnapshot(case_id="x", true_concepts=["should not be accepted"])
