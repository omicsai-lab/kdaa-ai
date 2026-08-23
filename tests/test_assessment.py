"""WP2 final correction 1 and 3: ownership-driven attribution uncertainty/review, and
assessment scoring_version.
"""

from __future__ import annotations

import json
from datetime import date

from kdaa.assessment.credibility import assess_asset_records
from kdaa.config import KDAAConfig
from kdaa.discovery.features import extract_trace_features
from kdaa.models import AssetAssessment, OwnershipState
from kdaa.ontology import Ontology

_AS_OF_DATE = date(2026, 6, 1)


def _assess(bundle):
    ontology = Ontology.default()
    config = KDAAConfig()
    features = extract_trace_features(bundle.traces, ontology)
    from kdaa.discovery.rules import discover_asset_hypotheses

    assets = discover_asset_hypotheses(bundle, features, ontology, config.discovery)
    return assess_asset_records(
        assets, bundle.traces, features, ontology, config.assessment, as_of_date=_AS_OF_DATE
    )


# --- Correction 1: unresolved ownership implies attribution uncertainty + review --------


def test_unresolved_ownership_increases_attribution_uncertainty() -> None:
    from kdaa.ingestion.synthetic import build_demo_bundle

    bundle = build_demo_bundle()
    assessed = _assess(bundle)
    assert assessed
    # Every rules.py-discovered asset defaults to UNRESOLVED ownership (see kdaa.discovery.rules).
    for asset in assessed:
        assert asset.ownership_state == OwnershipState.UNRESOLVED
        assert asset.assessment.attribution_confidence.uncertainty >= 0.42


def test_unresolved_ownership_requires_review() -> None:
    from kdaa.ingestion.synthetic import build_demo_bundle

    bundle = build_demo_bundle()
    assessed = _assess(bundle)
    for asset in assessed:
        assert asset.ownership_state == OwnershipState.UNRESOLVED
        assert asset.human_calibration_required is True


def _assess_single_asset_with_ownership(ownership_state: OwnershipState):
    """A controlled scenario: identical strong evidence (known LEAD role, several
    supporting traces, no relational/dependency signals) varying only in ownership_state,
    so any difference in uncertainty or human_calibration_required is attributable to
    ownership_state alone."""
    from kdaa.config import KDAAConfig
    from kdaa.discovery.features import extract_trace_features
    from kdaa.models import (
        AssetCategory,
        AssetRecord,
        ContributionRole,
        EvidenceLink,
        EvidenceRole,
        EvidenceTrace,
        SourceKind,
        TraceType,
    )
    from kdaa.ontology import Ontology

    traces = [
        EvidenceTrace(
            id=f"t{i}",
            unit_id="u1",
            trace_type=TraceType.SOFTWARE,
            title=f"Trace {i}",
            source_kind=SourceKind.MANUAL,
            contribution_role=ContributionRole.LEAD,
            event_date=_AS_OF_DATE,
        )
        for i in range(4)
    ]
    asset = AssetRecord(
        id="asset-1",
        unit_id="u1",
        label="Controlled evidence asset",
        bounded_claim="A bounded claim with strong support.",
        categories=[AssetCategory.CODIFIED],
        evidence_links=[EvidenceLink(trace_id=t.id, role=EvidenceRole.SUPPORTING) for t in traces],
        ownership_state=ownership_state,
    )
    ontology = Ontology.default()
    features = extract_trace_features(traces, ontology)
    assessed = assess_asset_records(
        [asset], traces, features, ontology, KDAAConfig().assessment, as_of_date=_AS_OF_DATE
    )
    return assessed[0]


def test_focal_unit_ownership_keeps_role_based_uncertainty_and_does_not_force_review() -> None:
    result = _assess_single_asset_with_ownership(OwnershipState.FOCAL_UNIT)
    assert result.ownership_state == OwnershipState.FOCAL_UNIT
    # Known LEAD role on every trace -> role-based uncertainty (0.15), not the 0.42
    # unresolved-ownership floor, since FOCAL_UNIT != UNRESOLVED.
    assert result.assessment.attribution_confidence.uncertainty == 0.15
    assert result.human_calibration_required is False


def test_unresolved_ownership_forces_review_holding_all_else_equal() -> None:
    # Same controlled setup as the FOCAL_UNIT case above, only ownership_state differs.
    focal = _assess_single_asset_with_ownership(OwnershipState.FOCAL_UNIT)
    unresolved = _assess_single_asset_with_ownership(OwnershipState.UNRESOLVED)
    assert focal.human_calibration_required is False
    assert unresolved.human_calibration_required is True
    assert focal.assessment.attribution_confidence.uncertainty == 0.15
    assert unresolved.assessment.attribution_confidence.uncertainty == 0.42


def test_shared_ownership_does_not_receive_unresolved_uncertainty_floor() -> None:
    from kdaa.config import KDAAConfig
    from kdaa.discovery.features import extract_trace_features
    from kdaa.models import (
        AssetCategory,
        AssetRecord,
        ContributionRole,
        EvidenceLink,
        EvidenceRole,
        EvidenceTrace,
        SourceKind,
        TraceType,
    )
    from kdaa.ontology import Ontology

    traces = [
        EvidenceTrace(
            id="t1",
            unit_id="u1",
            trace_type=TraceType.SOFTWARE,
            title="Trace 1",
            source_kind=SourceKind.MANUAL,
            contribution_role=ContributionRole.LEAD,
        )
    ]
    asset = AssetRecord(
        id="asset-1",
        unit_id="u1",
        label="Shared ownership asset",
        bounded_claim="A bounded claim.",
        categories=[AssetCategory.CODIFIED],
        evidence_links=[EvidenceLink(trace_id="t1", role=EvidenceRole.SUPPORTING)],
        ownership_state=OwnershipState.SHARED,
    )
    ontology = Ontology.default()
    features = extract_trace_features(traces, ontology)
    assessed = assess_asset_records(
        [asset], traces, features, ontology, KDAAConfig().assessment, as_of_date=_AS_OF_DATE
    )
    result = assessed[0]
    # SHARED with a known LEAD role: role-based uncertainty (0.15) applies, not the 0.42
    # unresolved-ownership floor, since SHARED != UNRESOLVED.
    assert result.assessment.attribution_confidence.uncertainty == 0.15
    # SHARED ownership alone does not force review through the unresolved-ownership clause.
    assert result.ownership_state == OwnershipState.SHARED


# --- Correction 3: assessment scoring_version -------------------------------------------


def test_newly_generated_assessment_uses_scoring_version_0_2_0() -> None:
    from kdaa.ingestion.synthetic import build_demo_bundle

    bundle = build_demo_bundle()
    assessed = _assess(bundle)
    assert assessed
    for asset in assessed:
        assert asset.assessment.scoring_version == "0.2.0"


def test_old_serialized_assessment_payload_without_scoring_version_still_loads() -> None:
    legacy_payload = {
        "evidence_strength": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "attribution_confidence": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "maturity": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "distinctiveness": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "tacitness": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "transferability": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "dependency_intensity": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "decay_risk": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "appropriability_risk": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "ai_interfaceability": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "privacy_risk": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "overall_credibility": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        # scoring_version deliberately omitted, as in pre-WP2/pre-correction payloads.
    }
    assessment = AssetAssessment.model_validate(legacy_payload)
    assert assessment.scoring_version == "0.1.0"
    restored = AssetAssessment.model_validate_json(json.dumps(legacy_payload))
    assert restored.scoring_version == "0.1.0"


def test_old_scoring_version_0_1_0_payload_round_trips_unchanged() -> None:
    legacy_payload = {
        "evidence_strength": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "attribution_confidence": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "maturity": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "distinctiveness": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "tacitness": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "transferability": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "dependency_intensity": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "decay_risk": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "appropriability_risk": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "ai_interfaceability": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "privacy_risk": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "overall_credibility": {"value": 0.5, "method": "m", "uncertainty": 0.2, "is_proxy": True},
        "scoring_version": "0.1.0",
    }
    assessment = AssetAssessment.model_validate(legacy_payload)
    assert assessment.scoring_version == "0.1.0"
