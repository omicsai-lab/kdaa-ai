import pytest
from pydantic import ValidationError

from kdaa.evaluation.paper_b import OwnershipLabel
from kdaa.evaluation.paper_b.truth import TrueAssetConcept, TrueOpportunityRelevance, TruthBundle


def test_truth_bundle_round_trip() -> None:
    bundle = TruthBundle(
        case_id="case-1",
        asset_concepts=[
            TrueAssetConcept(
                concept_id="concept-1",
                canonical_label="Federated evaluation pipelines",
                aliases=["federated eval"],
                ownership_state=OwnershipLabel.SHARED,
                supporting_trace_ids=["t1", "t2"],
            )
        ],
        opportunity_relevance=[TrueOpportunityRelevance(opportunity_id="o1", relevance_grade=3)],
        sensitive_trace_ids=["t3"],
    )
    restored = TruthBundle.model_validate_json(bundle.model_dump_json())
    assert restored == bundle


def test_truth_bundle_rejects_duplicate_concept_ids() -> None:
    with pytest.raises(ValidationError):
        TruthBundle(
            case_id="case-1",
            asset_concepts=[
                TrueAssetConcept(concept_id="dup", canonical_label="A"),
                TrueAssetConcept(concept_id="dup", canonical_label="B"),
            ],
        )


def test_truth_bundle_rejects_duplicate_opportunity_relevance() -> None:
    with pytest.raises(ValidationError):
        TruthBundle(
            case_id="case-1",
            opportunity_relevance=[
                TrueOpportunityRelevance(opportunity_id="dup", relevance_grade=1),
                TrueOpportunityRelevance(opportunity_id="dup", relevance_grade=2),
            ],
        )


def test_opportunity_relevance_grade_is_bounded_zero_to_three() -> None:
    TrueOpportunityRelevance(opportunity_id="o1", relevance_grade=0)
    TrueOpportunityRelevance(opportunity_id="o1", relevance_grade=3)
    with pytest.raises(ValidationError):
        TrueOpportunityRelevance(opportunity_id="o1", relevance_grade=4)
    with pytest.raises(ValidationError):
        TrueOpportunityRelevance(opportunity_id="o1", relevance_grade=-1)


def test_truth_bundle_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TruthBundle(case_id="case-1", not_a_real_field=True)
