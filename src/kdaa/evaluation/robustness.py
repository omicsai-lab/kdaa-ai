"""Deterministic perturbation suite for engineering robustness.

The suite uses a fully synthetic focal unit and controlled transformations. It
measures expected directional behavior; it does not establish real-world
construct validity or usefulness.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from statistics import mean

from kdaa.config import KDAAConfig
from kdaa.ingestion.synthetic import build_demo_bundle
from kdaa.models import ContributionRole, EvidenceTrace, SourceKind, TraceType, UnitBundle
from kdaa.pipeline import KDAAPipeline


@dataclass(frozen=True)
class RobustnessResult:
    base_asset_count: int
    base_mean_credibility: float
    duplicate_signature_jaccard: float
    duplicate_asset_count_delta: int
    duplicate_mean_credibility_delta: float
    stale_signature_jaccard: float
    stale_mean_credibility_delta: float
    unknown_role_signature_jaccard: float
    unknown_role_attribution_delta: float
    dropped_trace_signature_jaccard: float
    irrelevant_noise_signature_jaccard: float
    all_cases_provenance_complete: bool
    all_cases_zero_auto_confirmation: bool
    notes: list[str]


def _asset_signature(run) -> set[tuple[str, tuple[str, ...]]]:
    return {
        (asset.label, tuple(sorted(asset.concept_tags)))
        for asset in run.assets
    }


def _jaccard(left: set, right: set) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _mean_dimension(run, dimension: str) -> float:
    values = []
    for asset in run.assets:
        assessment = asset.assessment
        if assessment is None:
            continue
        values.append(float(getattr(assessment, dimension).value))
    return mean(values) if values else 0.0


def _provenance_complete(run) -> bool:
    trace_ids = {trace.id for trace in run.traces}
    return all(
        any(
            link.role.value == "supporting" and link.trace_id in trace_ids
            for link in asset.evidence_links
        )
        for asset in run.assets
    )


def _duplicate_bundle(bundle: UnitBundle) -> UnitBundle:
    duplicates = [
        trace.model_copy(
            update={
                "id": f"{trace.id}-duplicate",
                "raw": {**trace.raw, "synthetic_perturbation": "duplicate"},
            }
        )
        for trace in bundle.traces[:3]
    ]
    return bundle.model_copy(
        update={
            "traces": [*bundle.traces, *duplicates],
            "metadata": {**bundle.metadata, "perturbation": "duplicate_first_three_traces"},
        }
    )


def _stale_bundle(bundle: UnitBundle) -> UnitBundle:
    traces = [
        trace.model_copy(
            update={
                "event_date": date(2010, 1, 1),
                "raw": {**trace.raw, "synthetic_perturbation": "stale"},
            }
        )
        for trace in bundle.traces
    ]
    return bundle.model_copy(
        update={
            "traces": traces,
            "metadata": {**bundle.metadata, "perturbation": "all_evidence_stale"},
        }
    )


def _unknown_role_bundle(bundle: UnitBundle) -> UnitBundle:
    traces = [
        trace.model_copy(
            update={
                "contribution_role": ContributionRole.UNKNOWN,
                "raw": {**trace.raw, "synthetic_perturbation": "unknown_attribution"},
            }
        )
        for trace in bundle.traces
    ]
    return bundle.model_copy(
        update={
            "traces": traces,
            "metadata": {**bundle.metadata, "perturbation": "all_roles_unknown"},
        }
    )


def _dropped_trace_bundle(bundle: UnitBundle) -> UnitBundle:
    return bundle.model_copy(
        update={
            "traces": bundle.traces[1:],
            "metadata": {**bundle.metadata, "perturbation": "drop_first_trace"},
        }
    )


def _irrelevant_noise_bundle(bundle: UnitBundle) -> UnitBundle:
    noise = [
        EvidenceTrace(
            id=f"trace-noise-{index:02d}",
            unit_id=bundle.unit.id,
            trace_type=TraceType.OTHER,
            title=f"Synthetic administrative note {index}",
            description=(
                "Room scheduling, catering counts, parking validation, desk allocation, "
                "and generic office coordination."
            ),
            source_kind=SourceKind.SYNTHETIC,
            source_name="KDAA robustness generator",
            event_date=date(2026, 1, min(index + 1, 28)),
            contribution_role=ContributionRole.PARTICIPANT,
            raw={"synthetic_perturbation": "irrelevant_noise"},
        )
        for index in range(5)
    ]
    return bundle.model_copy(
        update={
            "traces": [*bundle.traces, *noise],
            "metadata": {**bundle.metadata, "perturbation": "irrelevant_noise"},
        }
    )


def run_robustness_suite(
    *,
    config: KDAAConfig | None = None,
    output_dir: str | Path | None = None,
) -> tuple[RobustnessResult, list[dict[str, object]]]:
    suite_config = config or KDAAConfig()
    if suite_config.mode != "deterministic":
        suite_config = suite_config.model_copy(update={"mode": "deterministic"})
    pipeline = KDAAPipeline(suite_config)
    base_bundle = build_demo_bundle()

    cases = {
        "base": base_bundle,
        "duplicate": _duplicate_bundle(base_bundle),
        "stale": _stale_bundle(base_bundle),
        "unknown_role": _unknown_role_bundle(base_bundle),
        "dropped_trace": _dropped_trace_bundle(base_bundle),
        "irrelevant_noise": _irrelevant_noise_bundle(base_bundle),
    }
    runs = {name: pipeline.analyze(bundle)[0] for name, bundle in cases.items()}
    base = runs["base"]
    base_signature = _asset_signature(base)
    base_credibility = _mean_dimension(base, "overall_credibility")
    base_attribution = _mean_dimension(base, "attribution_confidence")

    rows: list[dict[str, object]] = []
    for name, run in runs.items():
        rows.append(
            {
                "case": name,
                "traces": len(run.traces),
                "assets": len(run.assets),
                "mean_credibility": _mean_dimension(run, "overall_credibility"),
                "mean_attribution_confidence": _mean_dimension(
                    run, "attribution_confidence"
                ),
                "signature_jaccard_vs_base": _jaccard(
                    base_signature, _asset_signature(run)
                ),
                "provenance_complete": _provenance_complete(run),
                "auto_confirmed_assets": len(run.confirmed_assets),
            }
        )

    duplicate = runs["duplicate"]
    stale = runs["stale"]
    unknown = runs["unknown_role"]
    dropped = runs["dropped_trace"]
    noise = runs["irrelevant_noise"]
    result = RobustnessResult(
        base_asset_count=len(base.assets),
        base_mean_credibility=base_credibility,
        duplicate_signature_jaccard=_jaccard(base_signature, _asset_signature(duplicate)),
        duplicate_asset_count_delta=len(duplicate.assets) - len(base.assets),
        duplicate_mean_credibility_delta=(
            _mean_dimension(duplicate, "overall_credibility") - base_credibility
        ),
        stale_signature_jaccard=_jaccard(base_signature, _asset_signature(stale)),
        stale_mean_credibility_delta=(
            _mean_dimension(stale, "overall_credibility") - base_credibility
        ),
        unknown_role_signature_jaccard=_jaccard(
            base_signature, _asset_signature(unknown)
        ),
        unknown_role_attribution_delta=(
            _mean_dimension(unknown, "attribution_confidence") - base_attribution
        ),
        dropped_trace_signature_jaccard=_jaccard(
            base_signature, _asset_signature(dropped)
        ),
        irrelevant_noise_signature_jaccard=_jaccard(
            base_signature, _asset_signature(noise)
        ),
        all_cases_provenance_complete=all(_provenance_complete(run) for run in runs.values()),
        all_cases_zero_auto_confirmation=all(not run.confirmed_assets for run in runs.values()),
        notes=[
            "Perturbations are synthetic engineering checks, not empirical validity evidence.",
            "Exact/source-record-equivalent duplicates are retained in provenance but excluded from analytical support counts.",
            "Stale dates should reduce credibility through the declared recency component without changing the ontology.",
            "Unknown contribution roles should reduce attribution confidence without automatically deleting evidence.",
            "Irrelevant administrative noise should not materially alter the asset signature.",
        ],
    )

    if output_dir is not None:
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "robustness_summary.json").write_text(
            json.dumps(asdict(result), indent=2), encoding="utf-8"
        )
        with (output / "robustness_cases.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    return result, rows
