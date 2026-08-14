from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.models import AssetState, UnitBundle


def test_demo_bundle_roundtrip() -> None:
    bundle = build_demo_bundle()
    payload = bundle.model_dump_json()
    restored = UnitBundle.model_validate_json(payload)
    assert restored.unit.is_synthetic
    assert len(restored.traces) >= 15
    assert all(trace.unit_id == restored.unit.id for trace in restored.traces)


def test_initial_assets_are_never_confirmed_by_model_default() -> None:
    assert AssetState.HYPOTHESIS.value == "hypothesis"
