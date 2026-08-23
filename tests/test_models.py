import inspect
import json

import pytest
from pydantic import ValidationError

from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.models import (
    AssetCategory,
    AssetRecord,
    AssetState,
    ContributionRole,
    EvidenceLink,
    EvidenceRole,
    EvidenceTrace,
    FocalUnit,
    OwnershipState,
    SourceKind,
    TraceRelation,
    TraceRelationType,
    TraceType,
    UnitBundle,
    UnitType,
)


def test_demo_bundle_roundtrip() -> None:
    bundle = build_demo_bundle()
    payload = bundle.model_dump_json()
    restored = UnitBundle.model_validate_json(payload)
    assert restored.unit.is_synthetic
    assert len(restored.traces) >= 15
    assert all(trace.unit_id == restored.unit.id for trace in restored.traces)


def test_initial_assets_are_never_confirmed_by_model_default() -> None:
    assert AssetState.HYPOTHESIS.value == "hypothesis"


# --- A1: production/evaluation ownership enum compatibility -----------------------------


def test_ownership_state_matches_paper_b_ownership_label_value_set() -> None:
    from kdaa.evaluation.paper_b import OwnershipLabel

    assert {member.value for member in OwnershipState} == {member.value for member in OwnershipLabel}


def test_production_models_module_does_not_import_paper_b_evaluation_code() -> None:
    # The dependency direction runs one way: evaluation/adapter code may import kdaa.models,
    # but kdaa.models must never import kdaa.evaluation.paper_b. Checked via AST (actual
    # import statements only) rather than a substring scan, since the module's own
    # docstring legitimately *mentions* kdaa.evaluation.paper_b.OwnershipLabel in prose.
    import ast

    import kdaa.models as models_module

    tree = ast.parse(inspect.getsource(models_module))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "evaluation" not in alias.name, alias.name
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert "evaluation" not in node.module, node.module


# --- A3: ownership_state migration behavior ----------------------------------------------


def _minimal_asset_kwargs(**overrides) -> dict:
    base = dict(
        id="asset-1",
        unit_id="unit-1",
        label="Test asset",
        bounded_claim="A bounded claim.",
        categories=[AssetCategory.CODIFIED],
        evidence_links=[EvidenceLink(trace_id="trace-1", role=EvidenceRole.SUPPORTING)],
    )
    base.update(overrides)
    return base


def test_migration_explicit_legacy_focal_unit_token() -> None:
    asset = AssetRecord(**_minimal_asset_kwargs(hypothesized_owner="focal_unit"))
    assert asset.ownership_state == OwnershipState.FOCAL_UNIT


def test_migration_explicit_legacy_shared_token() -> None:
    asset = AssetRecord(**_minimal_asset_kwargs(hypothesized_owner="shared"))
    assert asset.ownership_state == OwnershipState.SHARED


def test_migration_arbitrary_display_name_maps_to_unresolved() -> None:
    for display_name in ("Maya Chen", "Georgetown University", "octocat", "The Data Lab"):
        asset = AssetRecord(**_minimal_asset_kwargs(hypothesized_owner=display_name))
        assert asset.ownership_state == OwnershipState.UNRESOLVED, display_name


def test_migration_missing_legacy_and_typed_fields_defaults_to_unresolved() -> None:
    kwargs = _minimal_asset_kwargs()
    kwargs.pop("hypothesized_owner", None)
    asset = AssetRecord(**kwargs)
    assert asset.ownership_state == OwnershipState.UNRESOLVED
    # The deprecated legacy display field still gets its own unrelated model default.
    assert asset.hypothesized_owner == "focal_unit"


def test_migration_explicit_typed_state_overrides_legacy_text() -> None:
    asset = AssetRecord(
        **_minimal_asset_kwargs(
            hypothesized_owner="focal_unit",
            ownership_state=OwnershipState.SHARED,
        )
    )
    assert asset.ownership_state == OwnershipState.SHARED


def test_migration_round_trip_serialization() -> None:
    original = AssetRecord(**_minimal_asset_kwargs(hypothesized_owner="Maya Chen"))
    assert original.ownership_state == OwnershipState.UNRESOLVED
    restored = AssetRecord.model_validate_json(original.model_dump_json())
    assert restored.ownership_state == OwnershipState.UNRESOLVED
    restored_dict_round_trip = AssetRecord.model_validate(original.model_dump(mode="json"))
    assert restored_dict_round_trip.ownership_state == OwnershipState.UNRESOLVED


def test_new_asset_with_no_attribution_evidence_defaults_to_unresolved() -> None:
    asset = AssetRecord(**_minimal_asset_kwargs())
    assert asset.ownership_state == OwnershipState.UNRESOLVED


def test_ownership_state_is_not_inferred_from_focal_unit_identity() -> None:
    # Constructing an asset whose hypothesized_owner equals the focal unit's own display
    # name (the common real-world shape) must not be interpreted as FOCAL_UNIT ownership.
    asset = AssetRecord(**_minimal_asset_kwargs(hypothesized_owner="Acme Robotics Lab"))
    assert asset.ownership_state == OwnershipState.UNRESOLVED


# --- A5: contribution role is not ownership -----------------------------------------------


@pytest.mark.parametrize(
    "role",
    [ContributionRole.LEAD, ContributionRole.ORIGINATOR, ContributionRole.IMPLEMENTER],
)
@pytest.mark.parametrize(
    "ownership_state",
    [OwnershipState.FOCAL_UNIT, OwnershipState.SHARED, OwnershipState.UNRESOLVED],
)
def test_contribution_role_can_coexist_with_any_ownership_state(role, ownership_state) -> None:
    trace = EvidenceTrace(
        id="trace-1",
        unit_id="unit-1",
        trace_type=TraceType.SOFTWARE,
        title="Example trace",
        contribution_role=role,
    )
    asset = AssetRecord(
        **_minimal_asset_kwargs(ownership_state=ownership_state)
    )
    # No validation coupling between the two fields: both independently valid.
    assert trace.contribution_role == role
    assert asset.ownership_state == ownership_state


# --- B1: TraceRelation and UnitBundle.trace_relations --------------------------------------


def test_trace_relation_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        TraceRelation(
            id="",
            source_trace_id="t1",
            target_trace_id="t2",
            relation_type=TraceRelationType.EXACT_DUPLICATE,
        )


def test_trace_relation_rejects_matching_source_and_target() -> None:
    with pytest.raises(ValidationError):
        TraceRelation(
            id="r1",
            source_trace_id="t1",
            target_trace_id="t1",
            relation_type=TraceRelationType.EXACT_DUPLICATE,
        )


def test_trace_relation_confidence_is_bounded() -> None:
    TraceRelation(
        id="r1", source_trace_id="t1", target_trace_id="t2",
        relation_type=TraceRelationType.OTHER, confidence=0.0,
    )
    TraceRelation(
        id="r2", source_trace_id="t1", target_trace_id="t2",
        relation_type=TraceRelationType.OTHER, confidence=1.0,
    )
    with pytest.raises(ValidationError):
        TraceRelation(
            id="r3", source_trace_id="t1", target_trace_id="t2",
            relation_type=TraceRelationType.OTHER, confidence=1.5,
        )
    with pytest.raises(ValidationError):
        TraceRelation(
            id="r4", source_trace_id="t1", target_trace_id="t2",
            relation_type=TraceRelationType.OTHER, confidence=-0.1,
        )


def _bundle_with_two_traces() -> tuple[FocalUnit, list[EvidenceTrace]]:
    unit = FocalUnit(id="unit-1", name="Test Unit", unit_type=UnitType.RESEARCHER)
    traces = [
        EvidenceTrace(
            id="t1", unit_id="unit-1", trace_type=TraceType.SOFTWARE, title="Trace 1",
            source_kind=SourceKind.MANUAL,
        ),
        EvidenceTrace(
            id="t2", unit_id="unit-1", trace_type=TraceType.SOFTWARE, title="Trace 2",
            source_kind=SourceKind.MANUAL,
        ),
    ]
    return unit, traces


def test_unit_bundle_accepts_well_formed_trace_relations() -> None:
    unit, traces = _bundle_with_two_traces()
    relation = TraceRelation(
        id="r1", source_trace_id="t1", target_trace_id="t2",
        relation_type=TraceRelationType.EXACT_DUPLICATE,
    )
    bundle = UnitBundle(unit=unit, traces=traces, trace_relations=[relation])
    assert bundle.trace_relations == [relation]


def test_unit_bundle_rejects_duplicate_relation_ids() -> None:
    unit, traces = _bundle_with_two_traces()
    relation_a = TraceRelation(
        id="dup", source_trace_id="t1", target_trace_id="t2",
        relation_type=TraceRelationType.EXACT_DUPLICATE,
    )
    relation_b = TraceRelation(
        id="dup", source_trace_id="t2", target_trace_id="t1",
        relation_type=TraceRelationType.OTHER,
    )
    with pytest.raises(ValidationError):
        UnitBundle(unit=unit, traces=traces, trace_relations=[relation_a, relation_b])


def test_unit_bundle_rejects_relation_referencing_unknown_trace() -> None:
    unit, traces = _bundle_with_two_traces()
    relation = TraceRelation(
        id="r1", source_trace_id="t1", target_trace_id="does-not-exist",
        relation_type=TraceRelationType.EXACT_DUPLICATE,
    )
    with pytest.raises(ValidationError):
        UnitBundle(unit=unit, traces=traces, trace_relations=[relation])


def test_unit_bundle_without_trace_relations_still_loads() -> None:
    # Backward compatibility: pre-WP2 bundles never had this field.
    unit, traces = _bundle_with_two_traces()
    bundle = UnitBundle(unit=unit, traces=traces)
    assert bundle.trace_relations == []
    legacy_payload = {
        "unit": json.loads(unit.model_dump_json()),
        "traces": [json.loads(trace.model_dump_json()) for trace in traces],
    }
    restored = UnitBundle.model_validate_json(json.dumps(legacy_payload))
    assert restored.trace_relations == []


def test_legacy_related_trace_ids_field_still_loads() -> None:
    trace = EvidenceTrace(
        id="t1", unit_id="unit-1", trace_type=TraceType.SOFTWARE, title="Trace",
        related_trace_ids=["t2"],
    )
    assert trace.related_trace_ids == ["t2"]
