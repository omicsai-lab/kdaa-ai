import pytest

from kdaa.config import KDAAConfig
from kdaa.ingestion.synthetic import build_demo_scenario
from kdaa.pipeline import KDAAPipeline


@pytest.mark.parametrize("scenario,unit_type", [("researcher", "researcher"), ("lab", "laboratory"), ("team", "team")])
def test_demo_scenarios_are_distinct_and_runnable(scenario: str, unit_type: str) -> None:
    bundle = build_demo_scenario(scenario)
    assert bundle.unit.unit_type.value == unit_type
    assert bundle.unit.is_synthetic is True
    assert len(bundle.traces) >= 10
    run, _ = KDAAPipeline(KDAAConfig()).analyze(bundle)
    assert run.unit.id == bundle.unit.id
    assert run.assets
    assert all(asset.epistemic_state.value != "confirmed" for asset in run.assets)


def test_unknown_demo_scenario_fails() -> None:
    with pytest.raises(ValueError):
        build_demo_scenario("unknown")
