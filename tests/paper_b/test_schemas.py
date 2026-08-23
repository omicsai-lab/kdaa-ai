import pytest
from pydantic import ValidationError

from kdaa.evaluation.paper_b import (
    AttributionRegime,
    CaseManifest,
    DomainBreadth,
    EvidenceDensity,
    EvidenceSnapshotTrace,
    ExperimentUnitType,
    InputSnapshot,
    OpportunityCandidate,
    OwnershipLabel,
    PredictedClaim,
    PredictedOpportunity,
    PredictionBundle,
)
from kdaa.models import AssetRecord


def _case_manifest(**overrides) -> CaseManifest:
    defaults = dict(
        case_id="case-1",
        unit_type=ExperimentUnitType.INDIVIDUAL_RESEARCHER,
        evidence_density=EvidenceDensity.SPARSE,
        domain_breadth=DomainBreadth.SINGLE_DOMAIN,
        attribution_regime=AttributionRegime.CLEAR_INDIVIDUAL,
    )
    defaults.update(overrides)
    return CaseManifest(**defaults)


def test_case_manifest_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        _case_manifest(unexpected_field="x")


def test_case_manifest_challenge_flag_and_category_must_agree() -> None:
    with pytest.raises(ValidationError):
        _case_manifest(is_challenge_case=True)
    with pytest.raises(ValidationError):
        _case_manifest(challenge_category="ontology_shift_and_unseen_synonyms")


def test_input_snapshot_is_frozen_and_order_is_fixed() -> None:
    snapshot = InputSnapshot(
        case_id="case-1",
        traces=(
            EvidenceSnapshotTrace(trace_id="t1", order_index=0),
            EvidenceSnapshotTrace(trace_id="t2", order_index=1),
        ),
        opportunity_catalog=(OpportunityCandidate(opportunity_id="o1"),),
    )
    with pytest.raises(ValidationError):
        snapshot.case_id = "other"
    with pytest.raises(ValidationError):
        snapshot.traces[0].trace_id = "changed"
    with pytest.raises(AttributeError):
        snapshot.traces.append(EvidenceSnapshotTrace(trace_id="t3", order_index=2))


def test_input_snapshot_rejects_unordered_or_duplicate_traces() -> None:
    with pytest.raises(ValidationError):
        InputSnapshot(
            case_id="case-1",
            traces=(
                EvidenceSnapshotTrace(trace_id="t1", order_index=1),
                EvidenceSnapshotTrace(trace_id="t2", order_index=0),
            ),
        )
    with pytest.raises(ValidationError):
        InputSnapshot(
            case_id="case-1",
            traces=(
                EvidenceSnapshotTrace(trace_id="dup", order_index=0),
                EvidenceSnapshotTrace(trace_id="dup", order_index=1),
            ),
        )


def test_prediction_bundle_represents_abstention_and_malformed_output() -> None:
    abstained = PredictionBundle(case_id="case-1", comparator_id="C1")
    assert abstained.claims == []

    malformed = PredictionBundle(
        case_id="case-1",
        comparator_id="C1",
        is_valid_output=False,
        validation_notes=["invalid JSON from provider"],
        raw_output_ref="raw:abc123",
    )
    assert malformed.is_valid_output is False
    assert malformed.claims == []


def test_prediction_bundle_rejects_duplicate_claim_or_rank_ids() -> None:
    with pytest.raises(ValidationError):
        PredictionBundle(
            case_id="case-1",
            comparator_id="C1",
            claims=[PredictedClaim(claim_id="dup"), PredictedClaim(claim_id="dup")],
        )
    with pytest.raises(ValidationError):
        PredictionBundle(
            case_id="case-1",
            comparator_id="C1",
            ranked_opportunities=[
                PredictedOpportunity(opportunity_id="o1", rank=1),
                PredictedOpportunity(opportunity_id="o2", rank=1),
            ],
        )


def test_prediction_bundle_does_not_cap_candidate_counts() -> None:
    # The frozen fairness rule (<=10 candidates, exactly 10 ranked opportunities) is
    # enforced by a WP4 fairness validator, not by the data model: WP7's A8
    # ("unconstrained recombination") ablation must be able to represent candidate
    # explosion beyond 10 for diagnostic purposes.
    many_claims = [PredictedClaim(claim_id=f"k{i}") for i in range(25)]
    bundle = PredictionBundle(case_id="case-1", comparator_id="A8", claims=many_claims)
    assert len(bundle.claims) == 25


def test_ownership_label_matches_protocol_clarification_pc03() -> None:
    assert {label.value for label in OwnershipLabel} == {
        "focal_unit",
        "shared",
        "organizational",
        "external",
        "unresolved",
    }


def test_evaluation_schemas_do_not_subclass_or_reuse_production_asset_record() -> None:
    assert not issubclass(PredictionBundle, AssetRecord)
    assert not issubclass(PredictedClaim, AssetRecord)
    assert not issubclass(PredictedOpportunity, AssetRecord)
    # AssetRecord itself keeps its production strictness: an active record without
    # supporting evidence is still rejected exactly as before this work package.
    with pytest.raises(ValidationError):
        AssetRecord(
            id="a1",
            unit_id="u1",
            label="x",
            bounded_claim="x",
            categories=[],
            evidence_links=[],
        )
