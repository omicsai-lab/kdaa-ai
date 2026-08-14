"""File-based run storage for the MVP."""

from __future__ import annotations

import json
from pathlib import Path

from kdaa.models import AnalysisRun, CalibrationRecord, OutcomeRecord


def load_analysis_run(path: str | Path) -> AnalysisRun:
    source = Path(path)
    return AnalysisRun.model_validate_json(source.read_text(encoding="utf-8"))


def save_analysis_run(run: AnalysisRun, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(run.model_dump_json(indent=2), encoding="utf-8")


def load_calibration_records(path: str | Path) -> list[CalibrationRecord]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("calibration_records", [])
    return [CalibrationRecord.model_validate(item) for item in payload]


def load_outcome_records(path: str | Path) -> list[OutcomeRecord]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("outcome_records", [])
    return [OutcomeRecord.model_validate(item) for item in payload]
