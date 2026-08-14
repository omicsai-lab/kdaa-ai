import json
from pathlib import Path

import pytest
import yaml

from kdaa.config import KDAAConfig
from kdaa.ingestion.local import load_bundle, merge_bundles, parse_cv_document
from kdaa.ingestion.synthetic import build_demo_bundle, build_team_demo_bundle
from kdaa.models import (
    CalibrationAction,
    CalibrationRecord,
    GainVector,
    OutcomeRecord,
)
from kdaa.pipeline import KDAAPipeline
from kdaa.storage import (
    load_analysis_run,
    load_calibration_records,
    load_outcome_records,
    save_analysis_run,
)


def test_local_bundle_json_yaml_and_errors(tmp_path: Path) -> None:
    bundle = build_demo_bundle()
    json_path = tmp_path / "bundle.json"
    json_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    assert load_bundle(json_path).unit.id == bundle.unit.id

    yaml_path = tmp_path / "bundle.yaml"
    yaml_path.write_text(
        yaml.safe_dump(bundle.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )
    assert load_bundle(yaml_path).unit.id == bundle.unit.id

    with pytest.raises(FileNotFoundError):
        load_bundle(tmp_path / "missing.json")
    bad = tmp_path / "bundle.csv"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        load_bundle(bad)


def test_parse_cv_like_text_and_merge(tmp_path: Path) -> None:
    cv = tmp_path / "cv.txt"
    cv.write_text(
        """Publications

2025. A provenance-aware AI methods paper with a complete abstract and reusable examples.

Software

2026. kdaa-ai: a tested Python package with Docker, documentation, and evidence graphs.

Teaching

2024. Graduate course on generative AI, knowledge management, and reproducible software.
""",
        encoding="utf-8",
    )
    parsed = parse_cv_document(
        cv,
        unit_id="unit:cv-test",
        unit_name="Synthetic CV Unit",
        institution="Synthetic Institute",
    )
    assert parsed.unit.id == "unit:cv-test"
    assert parsed.traces[0].sensitive is True
    assert {trace.trace_type.value for trace in parsed.traces} >= {
        "document",
        "publication",
        "software_repository",
        "course",
    }

    merged = merge_bundles([build_demo_bundle(), build_team_demo_bundle()])
    assert merged.unit.id == "synthetic:maya-chen"
    assert all(trace.unit_id == merged.unit.id for trace in merged.traces)
    assert merged.metadata["merged_sources"] == 2
    with pytest.raises(ValueError):
        merge_bundles([])


def test_storage_round_trip_and_lifecycle_record_loaders(tmp_path: Path) -> None:
    run, _ = KDAAPipeline(KDAAConfig()).analyze(build_demo_bundle())
    run_path = tmp_path / "run.json"
    save_analysis_run(run, run_path)
    loaded = load_analysis_run(run_path)
    assert loaded.manifest.run_id == run.manifest.run_id

    calibration = CalibrationRecord(
        id="cal-storage",
        run_id=run.manifest.run_id,
        asset_id=run.assets[0].id,
        action=CalibrationAction.DEFER,
        notes="test",
    )
    calibration_list = tmp_path / "cal-list.json"
    calibration_list.write_text(
        json.dumps([calibration.model_dump(mode="json")]), encoding="utf-8"
    )
    assert load_calibration_records(calibration_list)[0].id == "cal-storage"

    calibration_dict = tmp_path / "cal-dict.json"
    calibration_dict.write_text(
        json.dumps({"calibration_records": [calibration.model_dump(mode="json")]}),
        encoding="utf-8",
    )
    assert load_calibration_records(calibration_dict)[0].action == CalibrationAction.DEFER

    outcome = OutcomeRecord(
        id="out-storage",
        run_id=run.manifest.run_id,
        opportunity_id=run.opportunities[0].id,
        baseline_description="manual",
        intervention_description="KDAA-assisted",
        observed_gain=GainVector(time=0.1),
    )
    outcome_path = tmp_path / "outcomes.json"
    outcome_path.write_text(
        json.dumps({"outcome_records": [outcome.model_dump(mode="json")]}),
        encoding="utf-8",
    )
    assert load_outcome_records(outcome_path)[0].opportunity_id == outcome.opportunity_id
