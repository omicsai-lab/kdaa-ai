"""Checkpoint B orchestration: C1/C2/C4 development comparisons, ablations, robustness.

DEVELOPMENT ONLY -- NOT FINAL PAPER RESULTS. This module is truth-authorized orchestration
(same status as ``dev_pilot.py``): it holds evidence and hidden truth together in one
process, but only ever passes the evidence half into an adapter.

Primary case value for C1/C2/C4 is the mean across all intended repeats (Freeze Section
16.2); a failed repeat contributes the documented failure value (0.0 for E1/E4) rather
than being dropped -- never best-of-N, never successful-run-only.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from statistics import mean

from kdaa.models import UnitBundle
from kdaa.ontology import Ontology
from kdaa.providers.base import JSONProvider

from .ablations import (
    apply_a1_no_provenance_gate,
    apply_a4_flat_unit_representation,
    apply_a6_no_opportunity_specific_matching,
)
from .adapters.c1_generic_llm import run_c1
from .adapters.c2_evidence_linked import run_c2
from .adapters.c3_deterministic import run_c3
from .adapters.c4_hybrid import run_c4
from .dev_cases import DevelopmentCase
from .dev_pilot import CaseScore, _score_prediction
from .robustness import (
    r1_exact_duplicate,
    r1_source_equivalent_duplicate,
    r2_substantial_irrelevant_evidence,
    r3_ontology_surface_shift,
)
from .schemas import PredictionBundle
from .snapshot import build_snapshot_for_case
from .telemetry import AttemptStatus, ExperimentAttempt

INTENDED_REPEATS = 3
DEVELOPMENT_LABEL = "DEVELOPMENT ONLY -- NOT FINAL PAPER RESULTS"


@dataclass(frozen=True)
class RepeatedCaseScore:
    case_id: str
    comparator_id: str
    n_intended_repeats: int
    n_successful_repeats: int
    mean_concept_f1: float
    mean_unsupported_claim_rate: float | None
    mean_false_individualization_rate: float | None
    mean_attribution_coverage: float | None
    mean_ndcg_at_5: float
    per_repeat_status: tuple[str, ...]


def _score_attempts(case: DevelopmentCase, attempts: list[ExperimentAttempt]) -> RepeatedCaseScore:
    f1_values: list[float] = []
    ndcg_values: list[float] = []
    e2_values: list[float] = []
    far_values: list[float] = []
    coverage_values: list[float] = []
    successful = 0

    for attempt in attempts:
        if attempt.status == AttemptStatus.SUCCESS and attempt.prediction is not None:
            successful += 1
            score = _score_prediction(case, attempt.prediction)
            f1_values.append(score.concept_f1)
            ndcg_values.append(score.ndcg_at_5 if score.is_valid_ranking else 0.0)
            e2_values.append(score.unsupported_claim_rate)
            if score.false_individualization_rate is not None:
                far_values.append(score.false_individualization_rate)
            if score.attribution_coverage is not None:
                coverage_values.append(score.attribution_coverage)
        else:
            # Failed intended run: WP1 failure policy (f1/ndcg_failed_run_value=0.0).
            f1_values.append(0.0)
            ndcg_values.append(0.0)

    return RepeatedCaseScore(
        case_id=case.manifest.case_id,
        comparator_id=attempts[0].comparator_id if attempts else "",
        n_intended_repeats=len(attempts),
        n_successful_repeats=successful,
        mean_concept_f1=mean(f1_values) if f1_values else 0.0,
        mean_unsupported_claim_rate=mean(e2_values) if e2_values else None,
        mean_false_individualization_rate=mean(far_values) if far_values else None,
        mean_attribution_coverage=mean(coverage_values) if coverage_values else None,
        mean_ndcg_at_5=mean(ndcg_values) if ndcg_values else 0.0,
        per_repeat_status=tuple(attempt.status.value for attempt in attempts),
    )


@dataclass(frozen=True)
class LLMPilotResult:
    label: str
    n_cases: int
    n_repeats: int
    runtime_seconds: float
    all_attempts: tuple[ExperimentAttempt, ...]
    repeated_scores: tuple[RepeatedCaseScore, ...]


def run_llm_development_pilot(
    cases: list[DevelopmentCase],
    *,
    provider_c1: JSONProvider,
    provider_c2: JSONProvider,
    provider_c4: JSONProvider,
    ontology: Ontology,
    as_of_date: date,
    n_repeats: int = INTENDED_REPEATS,
) -> LLMPilotResult:
    """Run C1, C2, and C4 for ``n_repeats`` intended repeats on every case in ``cases``
    (the caller is responsible for having already frozen the subset via
    ``dev_llm_subset.select_development_llm_subset``).

    ``provider_c1``/``provider_c2``/``provider_c4`` must share the same model
    configuration (Checkpoint B Section 5); passing genuinely different providers is a
    caller error this function does not itself detect -- see
    ``tests/paper_b/test_model_lock.py`` for the check that the pilot script uses one
    shared configuration.
    """
    started = time.monotonic()
    all_attempts: list[ExperimentAttempt] = []
    repeated_scores: list[RepeatedCaseScore] = []

    for case in cases:
        snapshot = build_snapshot_for_case(case)
        opportunities = [(o.opportunity_id, o.title, o.description) for o in snapshot.opportunity_catalog]
        evidence_texts = [t.normalized_text for t in snapshot.traces]
        evidence_items = [(t.trace_id, t.normalized_text) for t in snapshot.traces]

        c1_attempts = [
            run_c1(
                provider=provider_c1,
                unit_name=case.evidence_bundle.unit.name,
                unit_description=case.evidence_bundle.unit.description,
                evidence_texts=evidence_texts,
                opportunities=opportunities,
                case_id=case.manifest.case_id,
                attempt_number=repeat,
            )
            for repeat in range(1, n_repeats + 1)
        ]
        c2_attempts = [
            run_c2(
                provider=provider_c2,
                unit_name=case.evidence_bundle.unit.name,
                unit_description=case.evidence_bundle.unit.description,
                evidence_items=evidence_items,
                opportunities=opportunities,
                case_id=case.manifest.case_id,
                attempt_number=repeat,
            )
            for repeat in range(1, n_repeats + 1)
        ]
        c4_attempts = [
            run_c4(
                case.evidence_bundle,
                snapshot,
                ontology,
                provider_c4,
                as_of_date=as_of_date,
                attempt_number=repeat,
            )
            for repeat in range(1, n_repeats + 1)
        ]

        all_attempts.extend([*c1_attempts, *c2_attempts, *c4_attempts])
        repeated_scores.extend(
            [
                _score_attempts(case, c1_attempts),
                _score_attempts(case, c2_attempts),
                _score_attempts(case, c4_attempts),
            ]
        )

    runtime = time.monotonic() - started
    return LLMPilotResult(
        label=DEVELOPMENT_LABEL,
        n_cases=len(cases),
        n_repeats=n_repeats,
        runtime_seconds=runtime,
        all_attempts=tuple(all_attempts),
        repeated_scores=tuple(repeated_scores),
    )


# --- ablations -----------------------------------------------------------------------------


@dataclass(frozen=True)
class AblationCaseResult:
    case_id: str
    ablation_id: str
    baseline: CaseScore
    ablated: CaseScore


def run_ablations(
    cases: list[DevelopmentCase], ontology: Ontology, *, as_of_date: date
) -> list[AblationCaseResult]:
    """Run A1/A4/A6 against C3 (fully deterministic, no LLM/credentials required) for a
    small development subset. Each ablation transforms C3's own baseline prediction for
    that case (see ``ablations.py``); the baseline itself is scored once and reused for
    all three ablations to keep this cheap and directly comparable.
    """
    results: list[AblationCaseResult] = []
    for case in cases:
        snapshot = build_snapshot_for_case(case)
        baseline_prediction = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=as_of_date)
        baseline_score = _score_prediction(case, baseline_prediction)

        a1 = apply_a1_no_provenance_gate(baseline_prediction)
        a4 = apply_a4_flat_unit_representation(baseline_prediction)
        a6 = apply_a6_no_opportunity_specific_matching(baseline_prediction, snapshot)

        for ablation_id, ablated_prediction in (("A1", a1), ("A4", a4), ("A6", a6)):
            results.append(
                AblationCaseResult(
                    case_id=case.manifest.case_id,
                    ablation_id=ablation_id,
                    baseline=baseline_score,
                    ablated=_score_prediction(case, ablated_prediction),
                )
            )
    return results


# --- robustness ------------------------------------------------------------------------------


@dataclass(frozen=True)
class RobustnessCaseResult:
    case_id: str
    perturbation_id: str
    baseline: CaseScore
    perturbed: CaseScore
    claim_label_jaccard: float
    top_opportunity_unchanged: bool


def _claim_label_signature(prediction: PredictionBundle) -> frozenset[str]:
    return frozenset(claim.label for claim in prediction.claims)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 1.0


_PERTURBATIONS = {
    "R1_exact_duplicate": r1_exact_duplicate,
    "R1_source_equivalent_duplicate": r1_source_equivalent_duplicate,
    "R2_irrelevant_evidence": r2_substantial_irrelevant_evidence,
    "R3_ontology_surface_shift": r3_ontology_surface_shift,
}


def run_robustness(
    cases: list[DevelopmentCase], ontology: Ontology, *, as_of_date: date
) -> list[RobustnessCaseResult]:
    """Run R1/R2/R3 against C3 for a small development subset."""
    results: list[RobustnessCaseResult] = []
    for case in cases:
        snapshot = build_snapshot_for_case(case)
        baseline_prediction = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=as_of_date)
        baseline_score = _score_prediction(case, baseline_prediction)
        baseline_signature = _claim_label_signature(baseline_prediction)
        baseline_top = baseline_prediction.ranked_opportunities[0].opportunity_id if baseline_prediction.ranked_opportunities else None

        for perturbation_id, perturb in _PERTURBATIONS.items():
            perturbed_bundle: UnitBundle = perturb(case.evidence_bundle)
            perturbed_snapshot = build_snapshot_for_case(
                DevelopmentCase(
                    manifest=case.manifest,
                    evidence_bundle=perturbed_bundle,
                    truth=case.truth,
                    opportunity_catalog=case.opportunity_catalog,
                )
            )
            perturbed_prediction = run_c3(perturbed_bundle, perturbed_snapshot, ontology, as_of_date=as_of_date)
            perturbed_score = _score_prediction(case, perturbed_prediction)
            perturbed_top = (
                perturbed_prediction.ranked_opportunities[0].opportunity_id
                if perturbed_prediction.ranked_opportunities
                else None
            )
            results.append(
                RobustnessCaseResult(
                    case_id=case.manifest.case_id,
                    perturbation_id=perturbation_id,
                    baseline=baseline_score,
                    perturbed=perturbed_score,
                    claim_label_jaccard=_jaccard(baseline_signature, _claim_label_signature(perturbed_prediction)),
                    top_opportunity_unchanged=(baseline_top == perturbed_top),
                )
            )
    return results


# --- output writing --------------------------------------------------------------------------


def write_checkpoint_b_outputs(
    *,
    output_dir: str | Path,
    llm_result: LLMPilotResult,
    ablation_results: list[AblationCaseResult],
    robustness_results: list[RobustnessCaseResult],
    provider_dry_run: bool,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    def _to_jsonable(value):
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "__dataclass_fields__"):
            return {k: _to_jsonable(v) for k, v in asdict(value).items()}
        if isinstance(value, (list, tuple)):
            return [_to_jsonable(v) for v in value]
        if isinstance(value, dict):
            return {k: _to_jsonable(v) for k, v in value.items()}
        return value

    (output / "llm_attempts.json").write_text(
        json.dumps([_to_jsonable(a) for a in llm_result.all_attempts], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output / "llm_repeated_scores.json").write_text(
        json.dumps([asdict(s) for s in llm_result.repeated_scores], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output / "ablation_results.json").write_text(
        json.dumps([_to_jsonable(r) for r in ablation_results], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output / "robustness_results.json").write_text(
        json.dumps([_to_jsonable(r) for r in robustness_results], indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output / "README_DEVELOPMENT_ONLY.txt").write_text(
        f"{DEVELOPMENT_LABEL}\n\n"
        "Checkpoint B: C1/C2/C4 development LLM comparisons, ablations (A1/A4/A6), and "
        "robustness (R1/R2/R3). Not the frozen final N=240 dataset; must not be cited as "
        "final evidence.\n\n"
        f"provider_dry_run={provider_dry_run} (True means fake-provider validation only, "
        "no live model call was made; see the accompanying report for what a live run "
        "requires).\n",
        encoding="utf-8",
    )
