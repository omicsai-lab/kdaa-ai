#!/usr/bin/env python3
"""Regenerate committed synthetic bundles and JSON schemas."""

from __future__ import annotations

import json
from pathlib import Path

from kdaa.ingestion.synthetic import (
    build_demo_bundle,
    build_lab_demo_bundle,
    build_team_demo_bundle,
)
from kdaa.models import AnalysisRun, CalibrationRecord, OutcomeRecord, UnitBundle

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "data" / "demo"
SCHEMA = ROOT / "data" / "schema"


def main() -> None:
    DEMO.mkdir(parents=True, exist_ok=True)
    SCHEMA.mkdir(parents=True, exist_ok=True)

    bundles = {
        "synthetic_researcher.json": build_demo_bundle(),
        "synthetic_lab.json": build_lab_demo_bundle(),
        "synthetic_team.json": build_team_demo_bundle(),
    }
    for filename, bundle in bundles.items():
        (DEMO / filename).write_text(bundle.model_dump_json(indent=2), encoding="utf-8")

    schemas = {
        "unit_bundle.schema.json": UnitBundle.model_json_schema(),
        "analysis_run.schema.json": AnalysisRun.model_json_schema(),
        "calibration_record.schema.json": CalibrationRecord.model_json_schema(),
        "outcome_record.schema.json": OutcomeRecord.model_json_schema(),
    }
    for filename, schema in schemas.items():
        (SCHEMA / filename).write_text(json.dumps(schema, indent=2), encoding="utf-8")

    print(f"Wrote {len(bundles)} synthetic bundles and {len(schemas)} schemas.")


if __name__ == "__main__":
    main()
