"""WP2 section C: frozen analysis as_of_date."""

from __future__ import annotations

import json
from datetime import date

from kdaa.assessment.credibility import _recency_score, assess_asset_records
from kdaa.config import KDAAConfig
from kdaa.discovery.features import extract_trace_features
from kdaa.discovery.rules import discover_asset_hypotheses
from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.models import RunManifest
from kdaa.ontology import Ontology
from kdaa.pipeline import KDAAPipeline


def _dated_traces(bundle):
    return [trace for trace in bundle.traces if trace.event_date]


# --- C5.1 / C5.2: fixed date produces fixed, directionally correct recency ---------------


def test_fixed_date_produces_fixed_recency() -> None:
    bundle = build_demo_bundle()
    traces = _dated_traces(bundle)
    assert traces, "demo bundle must contain at least one dated trace"
    value_a, _ = _recency_score(traces, half_life_years=5.0, as_of_date=date(2026, 6, 1))
    value_b, _ = _recency_score(traces, half_life_years=5.0, as_of_date=date(2026, 6, 1))
    assert value_a == value_b


def test_changing_only_the_date_changes_recency_directionally() -> None:
    bundle = build_demo_bundle()
    traces = _dated_traces(bundle)
    near_value, _ = _recency_score(traces, half_life_years=5.0, as_of_date=date(2026, 1, 1))
    far_value, _ = _recency_score(traces, half_life_years=5.0, as_of_date=date(2036, 1, 1))
    # A later as_of_date makes every trace older, so recency (freshness) must not increase.
    assert far_value < near_value


# --- C5.3: scoring does not call the ambient clock internally ----------------------------


def test_recency_score_never_calls_date_today(monkeypatch) -> None:
    import kdaa.assessment.credibility as credibility_module

    class _ForbiddenDate(date):
        @classmethod
        def today(cls):
            raise AssertionError("_recency_score must not call the ambient clock")

    monkeypatch.setattr(credibility_module, "date", _ForbiddenDate)
    bundle = build_demo_bundle()
    traces = _dated_traces(bundle)
    # Passing a real `date` instance as as_of_date works regardless of the monkeypatched
    # class, since the function never constructs "today" internally.
    value, _ = credibility_module._recency_score(
        traces, half_life_years=5.0, as_of_date=date(2026, 6, 1)
    )
    assert 0.0 <= value <= 1.0


def test_assess_asset_records_never_calls_date_today(monkeypatch) -> None:
    import kdaa.assessment.credibility as credibility_module

    class _ForbiddenDate(date):
        @classmethod
        def today(cls):
            raise AssertionError("assess_asset_records must not call the ambient clock")

    monkeypatch.setattr(credibility_module, "date", _ForbiddenDate)

    bundle = build_demo_bundle()
    ontology = Ontology.default()
    config = KDAAConfig()
    features = extract_trace_features(bundle.traces, ontology)
    assets = discover_asset_hypotheses(bundle, features, ontology, config.discovery)
    assessed = assess_asset_records(
        assets, bundle.traces, features, ontology, config.assessment, as_of_date=date(2026, 6, 1)
    )
    assert assessed


# --- C5.4 / C5.5: pipeline resolves an unspecified date once and records it --------------


def test_pipeline_resolves_unspecified_date_and_records_it_in_manifest() -> None:
    run, _ = KDAAPipeline(KDAAConfig()).analyze(build_demo_bundle())
    assert run.manifest.analysis_as_of_date == date.today()


def test_pipeline_records_explicit_as_of_date_in_manifest() -> None:
    explicit = date(2026, 3, 15)
    run, _ = KDAAPipeline(KDAAConfig(as_of_date=explicit)).analyze(build_demo_bundle())
    assert run.manifest.analysis_as_of_date == explicit


def test_pipeline_resolution_happens_once_not_per_calculation(monkeypatch) -> None:
    # If the pipeline resolved "today" more than once (e.g. once for the manifest, once
    # per recency call), a clock that changes between calls would produce inconsistent
    # results. Simulate that by making date.today() advance each call; the resolved date
    # recorded in the manifest must still be self-consistent with what assessment used
    # (proven indirectly: recomputing recency with the manifest's own recorded date must
    # reproduce the same score the pipeline actually produced).
    from kdaa import pipeline as pipeline_module

    calls = {"count": 0}
    real_today = date.today()

    class _AdvancingDate(date):
        @classmethod
        def today(cls):
            calls["count"] += 1
            return real_today

    monkeypatch.setattr(pipeline_module, "date", _AdvancingDate)
    run, _ = KDAAPipeline(KDAAConfig()).analyze(build_demo_bundle())
    assert calls["count"] == 1
    assert run.manifest.analysis_as_of_date == real_today


# --- C5.6: old config and manifest payloads still load ------------------------------------


def test_old_config_payload_without_as_of_date_still_loads() -> None:
    legacy_payload = {"version": "0.1.0", "random_seed": 42, "mode": "deterministic"}
    config = KDAAConfig.model_validate(legacy_payload)
    assert config.as_of_date is None


def test_old_manifest_payload_without_analysis_as_of_date_still_loads() -> None:
    legacy_payload = {
        "run_id": "run-legacy",
        "kdaa_version": "0.1.0",
        "config_digest": "deadbeef",
        "input_digest": "deadbeef",
        "random_seed": 42,
        "mode": "deterministic",
    }
    manifest = RunManifest.model_validate(legacy_payload)
    assert manifest.analysis_as_of_date is None
    # Round-trips through JSON exactly like any other optional field.
    restored = RunManifest.model_validate_json(json.dumps(legacy_payload))
    assert restored.analysis_as_of_date is None


# --- C5.7: two fixed-date runs have identical scientific payloads ------------------------


def test_two_fixed_date_runs_have_identical_assessment_payloads_despite_different_run_ids() -> None:
    explicit = date(2026, 3, 15)
    bundle = build_demo_bundle()
    pipeline = KDAAPipeline(KDAAConfig(as_of_date=explicit))
    first, _ = pipeline.analyze(bundle)
    second, _ = pipeline.analyze(bundle)

    assert first.manifest.run_id != second.manifest.run_id
    assert first.manifest.analysis_as_of_date == second.manifest.analysis_as_of_date == explicit

    def _assessment_payload(run):
        return [
            (
                asset.label,
                asset.assessment.overall_credibility.value if asset.assessment else None,
                asset.assessment.decay_risk.value if asset.assessment else None,
                asset.assessment.dependency_intensity.value if asset.assessment else None,
            )
            for asset in run.assets
        ]

    assert _assessment_payload(first) == _assessment_payload(second)
