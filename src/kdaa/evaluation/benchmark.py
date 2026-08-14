"""Synthetic benchmark runner.

The benchmark evaluates software behavior under known synthetic ground truth.
It is not a substitute for human validation or real-world outcome evidence.
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from kdaa.config import KDAAConfig
from kdaa.evaluation.baselines import FlatKeywordProfileBaseline
from kdaa.evaluation.metrics import set_metrics
from kdaa.ingestion.synthetic import SyntheticBenchmarkGenerator
from kdaa.ontology import Ontology
from kdaa.pipeline import KDAAPipeline


@dataclass(frozen=True)
class BenchmarkResult:
    n_units: int
    seed: int
    baseline_concept_precision: float
    baseline_concept_recall: float
    baseline_concept_f1: float
    kdaa_concept_precision: float
    kdaa_concept_recall: float
    kdaa_concept_f1: float
    baseline_provenance_completeness: float
    kdaa_provenance_completeness: float
    baseline_unsupported_claim_rate: float
    kdaa_unsupported_claim_rate: float
    kdaa_confirmed_without_human_rate: float
    kdaa_determinism_rate: float
    mean_runtime_seconds: float
    notes: list[str]


def _predicted_concept_keys(run: Any, ontology: Ontology) -> set[str]:
    label_to_key = {definition.label.lower(): key for key, definition in ontology.concepts.items()}
    predictions: set[str] = set()
    for asset in run.assets:
        if not asset.assessment:
            continue
        if asset.assessment.overall_credibility.value < 0.42:
            continue
        for label in asset.concept_tags:
            key = label_to_key.get(label.lower())
            if key:
                predictions.add(key)
    return predictions


def _provenance_completeness(run: Any) -> float:
    if not run.assets:
        return 1.0
    complete = 0
    for asset in run.assets:
        support = [link for link in asset.evidence_links if link.role.value == "supporting"]
        if support and all(link.trace_id for link in support):
            complete += 1
    return complete / len(run.assets)


def _unsupported_claim_rate(run: Any) -> float:
    if not run.assets:
        return 0.0
    unsupported = 0
    trace_ids = {trace.id for trace in run.traces}
    for asset in run.assets:
        support = [link.trace_id for link in asset.evidence_links if link.role.value == "supporting"]
        if not support or any(trace_id not in trace_ids for trace_id in support):
            unsupported += 1
    return unsupported / len(run.assets)


def _signature(run: Any) -> str:
    payload = [
        {
            "label": asset.label,
            "claim": asset.bounded_claim,
            "evidence": sorted(link.trace_id for link in asset.evidence_links),
            "state": asset.epistemic_state.value,
        }
        for asset in run.assets
    ]
    return json.dumps(payload, sort_keys=True)


def run_synthetic_benchmark(
    *,
    n_units: int = 50,
    seed: int = 42,
    config: KDAAConfig | None = None,
    output_dir: str | Path | None = None,
) -> tuple[BenchmarkResult, list[dict[str, Any]]]:
    benchmark_config = config or KDAAConfig()
    if benchmark_config.mode != "deterministic":
        benchmark_config = benchmark_config.model_copy(update={"mode": "deterministic"})
    ontology = Ontology.default()
    generator = SyntheticBenchmarkGenerator(seed=seed)
    pipeline = KDAAPipeline(benchmark_config, ontology=ontology)
    baseline = FlatKeywordProfileBaseline(max_concepts=8)

    rows: list[dict[str, Any]] = []
    determinism_checks: list[bool] = []
    for index, bundle in enumerate(generator.generate(n_units=n_units)):
        truth = set(bundle.metadata.get("ground_truth_concepts", []))
        baseline_result = baseline.run(bundle, ontology)
        baseline_metrics = set_metrics(baseline_result.predicted_concepts, truth)

        started = time.perf_counter()
        run, _ = pipeline.analyze(bundle)
        runtime = time.perf_counter() - started
        predicted = _predicted_concept_keys(run, ontology)
        kdaa_metrics = set_metrics(predicted, truth)
        if index < min(10, n_units):
            second_run, _ = pipeline.analyze(bundle)
            determinism_checks.append(_signature(run) == _signature(second_run))

        confirmed_without_human = sum(asset.epistemic_state.value == "confirmed" for asset in run.assets)
        rows.append(
            {
                "unit_id": bundle.unit.id,
                "truth_concepts": len(truth),
                "baseline_predicted_concepts": len(baseline_result.predicted_concepts),
                "baseline_precision": baseline_metrics.precision,
                "baseline_recall": baseline_metrics.recall,
                "baseline_f1": baseline_metrics.f1,
                "kdaa_predicted_concepts": len(predicted),
                "kdaa_precision": kdaa_metrics.precision,
                "kdaa_recall": kdaa_metrics.recall,
                "kdaa_f1": kdaa_metrics.f1,
                "baseline_provenance_completeness": baseline_result.provenance_completeness,
                "kdaa_provenance_completeness": _provenance_completeness(run),
                "baseline_unsupported_claim_rate": baseline_result.unsupported_claim_rate,
                "kdaa_unsupported_claim_rate": _unsupported_claim_rate(run),
                "kdaa_assets": len(run.assets),
                "kdaa_confirmed_without_human": confirmed_without_human,
                "runtime_seconds": runtime,
            }
        )

    result = BenchmarkResult(
        n_units=n_units,
        seed=seed,
        baseline_concept_precision=mean(row["baseline_precision"] for row in rows),
        baseline_concept_recall=mean(row["baseline_recall"] for row in rows),
        baseline_concept_f1=mean(row["baseline_f1"] for row in rows),
        kdaa_concept_precision=mean(row["kdaa_precision"] for row in rows),
        kdaa_concept_recall=mean(row["kdaa_recall"] for row in rows),
        kdaa_concept_f1=mean(row["kdaa_f1"] for row in rows),
        baseline_provenance_completeness=mean(
            row["baseline_provenance_completeness"] for row in rows
        ),
        kdaa_provenance_completeness=mean(row["kdaa_provenance_completeness"] for row in rows),
        baseline_unsupported_claim_rate=mean(
            row["baseline_unsupported_claim_rate"] for row in rows
        ),
        kdaa_unsupported_claim_rate=mean(row["kdaa_unsupported_claim_rate"] for row in rows),
        kdaa_confirmed_without_human_rate=(
            sum(row["kdaa_confirmed_without_human"] for row in rows)
            / max(1, sum(row["kdaa_assets"] for row in rows))
        ),
        kdaa_determinism_rate=mean(determinism_checks) if determinism_checks else 1.0,
        mean_runtime_seconds=mean(row["runtime_seconds"] for row in rows),
        notes=[
            "Synthetic ground truth is generated from the same declared ontology but not exposed to the pipeline at run time.",
            "Concept recovery is an engineering smoke test, not evidence that real latent assets are valid.",
            "The flat-profile baseline intentionally omits claim-level provenance and epistemic state.",
            "Human calibration and realized/captured value require later empirical studies.",
        ],
    )

    if output_dir is not None:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "benchmark_summary.json").write_text(
            json.dumps(asdict(result), indent=2), encoding="utf-8"
        )
        with (output / "benchmark_units.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
            if rows:
                writer.writeheader()
                writer.writerows(rows)
    return result, rows
