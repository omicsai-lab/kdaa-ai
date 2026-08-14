"""FastAPI service for programmatic use."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from kdaa.config import KDAAConfig
from kdaa.ingestion import build_demo_scenario
from kdaa.lifecycle import apply_calibration
from kdaa.models import AnalysisRun, CalibrationRecord, UnitBundle
from kdaa.pipeline import KDAAPipeline

app = FastAPI(
    title="KDAA-AI API",
    version="0.1.0",
    description=(
        "Provenance-aware discovery, assessment, and opportunity matching for provisional "
        "knowledge asset records."
    ),
)


class CalibrationRequest(BaseModel):
    run: AnalysisRun
    records: list[CalibrationRecord] = Field(default_factory=list)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/v1/schema/unit-bundle")
def unit_bundle_schema() -> dict:
    return UnitBundle.model_json_schema()


@app.post("/v1/analyze", response_model=AnalysisRun)
def analyze(bundle: UnitBundle) -> AnalysisRun:
    try:
        run, _ = KDAAPipeline(KDAAConfig()).analyze(bundle)
        return run
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/demo", response_model=AnalysisRun)
def demo(scenario: str = "researcher") -> AnalysisRun:
    try:
        bundle = build_demo_scenario(scenario)
        run, _ = KDAAPipeline(KDAAConfig()).analyze(bundle)
        return run
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/calibrate", response_model=AnalysisRun)
def calibrate(request: CalibrationRequest) -> AnalysisRun:
    try:
        return apply_calibration(request.run, request.records)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
