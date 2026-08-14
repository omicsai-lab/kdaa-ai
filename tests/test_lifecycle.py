from kdaa.config import KDAAConfig
from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.lifecycle import apply_calibration
from kdaa.models import CalibrationAction, CalibrationRecord
from kdaa.pipeline import KDAAPipeline


def test_calibration_preserves_delta_and_can_confirm() -> None:
    run, _ = KDAAPipeline(KDAAConfig()).analyze(build_demo_bundle())
    asset = run.assets[0]
    record = CalibrationRecord(
        id="cal-test",
        run_id=run.manifest.run_id,
        asset_id=asset.id,
        action=CalibrationAction.CONFIRM,
        notes="Synthetic confirmation for unit test only.",
    )
    updated = apply_calibration(run, [record])
    updated_asset = next(item for item in updated.assets if item.id == asset.id)
    assert updated_asset.epistemic_state.value == "confirmed"
    assert updated_asset.version == asset.version + 1
    assert len(updated.calibration_records) == 1
    original_asset = next(item for item in run.assets if item.id == asset.id)
    assert original_asset.epistemic_state.value != "confirmed"
