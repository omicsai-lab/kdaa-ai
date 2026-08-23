"""Checkpoint A development-pilot orchestration.

Ties together development-case generation, truth separation/leakage validation, the two
Checkpoint A comparators (C0-S, C3), E1-E4 scoring, and the paired development summary.

DEVELOPMENT ONLY -- NOT FINAL PAPER RESULTS. This module is truth-authorized orchestration
(it holds both the evidence and the hidden truth in the same process, which is expected
and safe here: the leakage check exists precisely to prove that only the evidence half is
ever passed into the adapters, not that the orchestrator itself never sees truth).
"""

from __future__ import annotations

import csv
import json
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from kdaa.ontology import Ontology

from .adapters.c0_semantic import run_c0_s
from .adapters.c3_deterministic import run_c3
from .analysis import PairedMetricSummary, summarize_paired
from .dev_cases import DevelopmentCase, generate_development_set
from .fairness import validate_case_fairness
from .leakage import validate_case_leakage
from .schemas import PredictionBundle
from .scoring import score_attribution, score_concepts, score_opportunities, score_semantic_support
from .snapshot import build_snapshot_for_case

DEVELOPMENT_LABEL = "DEVELOPMENT ONLY -- NOT FINAL PAPER RESULTS"


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    comparator_id: str
    concept_precision: float
    concept_recall: float
    concept_f1: float
    unsupported_claim_rate: float
    false_individualization_rate: float | None
    attribution_coverage: float | None
    unresolved_rate: float | None
    ndcg_at_5: float
    is_valid_ranking: bool


@dataclass(frozen=True)
class DevPilotResult:
    label: str
    n_cases: int
    as_of_date: str
    runtime_seconds: float
    case_scores: tuple[CaseScore, ...]
    paired_summaries: dict[str, PairedMetricSummary]


def _score_prediction(
    case: DevelopmentCase,
    prediction: PredictionBundle,
) -> CaseScore:
    concept_result = score_concepts(case.manifest.case_id, prediction.claims, case.truth.asset_concepts)
    semantic_result = score_semantic_support(
        case.manifest.case_id, prediction.claims, case.truth.asset_concepts, concept_result.matched_pairs
    )
    attribution_result = score_attribution(
        case.manifest.case_id, prediction.claims, case.truth.asset_concepts, concept_result.matched_pairs
    )
    ndcg_result = score_opportunities(
        case.manifest.case_id, prediction.ranked_opportunities, case.truth.opportunity_relevance
    )
    return CaseScore(
        case_id=case.manifest.case_id,
        comparator_id=prediction.comparator_id,
        concept_precision=concept_result.precision,
        concept_recall=concept_result.recall,
        concept_f1=concept_result.f1,
        unsupported_claim_rate=semantic_result.unsupported_claim_rate,
        false_individualization_rate=attribution_result.false_individualization_rate,
        attribution_coverage=attribution_result.attribution_coverage,
        unresolved_rate=attribution_result.unresolved_rate,
        ndcg_at_5=ndcg_result.ndcg_at_5,
        is_valid_ranking=ndcg_result.is_valid_ranking,
    )


def run_development_pilot(
    *,
    n_cases: int = 60,
    as_of_date: date,
    bootstrap_seed: int = 42,
    ontology: Ontology | None = None,
) -> DevPilotResult:
    ontology = ontology or Ontology.default()
    started = time.monotonic()

    cases = generate_development_set(n_cases, ontology=ontology)

    case_scores: list[CaseScore] = []
    c0s_scores: dict[str, CaseScore] = {}
    c3_scores: dict[str, CaseScore] = {}

    for case in cases:
        snapshot = build_snapshot_for_case(case)
        validate_case_leakage(case.evidence_bundle, case.truth, snapshot)

        c0s_prediction = run_c0_s(snapshot, ontology)
        c3_prediction = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=as_of_date)

        validate_case_fairness(snapshot, c0s_prediction, snapshot, c3_prediction)

        c0s_score = _score_prediction(case, c0s_prediction)
        c3_score = _score_prediction(case, c3_prediction)
        case_scores.extend([c0s_score, c3_score])
        c0s_scores[case.manifest.case_id] = c0s_score
        c3_scores[case.manifest.case_id] = c3_score

    paired_summaries = _build_paired_summaries(cases, c0s_scores, c3_scores, bootstrap_seed)

    runtime = time.monotonic() - started
    return DevPilotResult(
        label=DEVELOPMENT_LABEL,
        n_cases=n_cases,
        as_of_date=as_of_date.isoformat(),
        runtime_seconds=runtime,
        case_scores=tuple(case_scores),
        paired_summaries=paired_summaries,
    )


def _build_paired_summaries(
    cases: list[DevelopmentCase],
    c0s_scores: dict[str, CaseScore],
    c3_scores: dict[str, CaseScore],
    seed: int,
) -> dict[str, PairedMetricSummary]:
    case_ids = [case.manifest.case_id for case in cases]

    def paired(attr: str, *, drop_none: bool = False) -> PairedMetricSummary:
        values_a, values_b = [], []
        for case_id in case_ids:
            a = getattr(c3_scores[case_id], attr)
            b = getattr(c0s_scores[case_id], attr)
            if drop_none and (a is None or b is None):
                continue
            values_a.append(a)
            values_b.append(b)
        return summarize_paired(attr, values_a, values_b, seed=seed)

    return {
        "concept_f1": paired("concept_f1"),
        "unsupported_claim_rate": paired("unsupported_claim_rate"),
        "false_individualization_rate": paired("false_individualization_rate", drop_none=True),
        "ndcg_at_5": paired("ndcg_at_5"),
    }


def write_development_outputs(result: DevPilotResult, output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    with (output / "case_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(asdict(result.case_scores[0]).keys()) if result.case_scores else []
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for score in result.case_scores:
            writer.writerow(asdict(score))

    summary_payload = {
        "label": result.label,
        "n_cases": result.n_cases,
        "as_of_date": result.as_of_date,
        "runtime_seconds": result.runtime_seconds,
        "paired_summaries": {
            name: asdict(summary) for name, summary in result.paired_summaries.items()
        },
    }
    (output / "summary.json").write_text(json.dumps(summary_payload, indent=2, sort_keys=True), encoding="utf-8")
    (output / "README_DEVELOPMENT_ONLY.txt").write_text(
        f"{DEVELOPMENT_LABEL}\n\n"
        "This directory contains Checkpoint A development-pilot outputs only. It is not\n"
        "the frozen final N=240 dataset and must not be cited as final evidence.\n",
        encoding="utf-8",
    )
