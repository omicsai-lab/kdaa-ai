"""Final Paper B execution orchestration (Freeze: final deterministic block, final LLM
block, final ablations, final robustness, final paired comparisons).

**Implementation-only.** Nothing in this module generates or writes the frozen final
N=240 dataset -- it operates on whatever ``list[FinalCase]`` it is given, so it can be
exercised end-to-end (this checkpoint) against in-memory or temporary-directory cases with
a fake provider, and later against the real frozen dataset with the real model, without any
code change.

Deliberately thin: every actual scoring computation, comparator adapter, ablation
transform, robustness perturbation, and paired-statistics routine is imported unchanged
from the already-frozen Checkpoint A/B modules (``dev_pilot``, ``dev_pilot_llm``,
``ablations``, ``robustness``, ``analysis``, ``adapters``) -- this module only reuses them
under final-appropriate labeling and against ``FinalCase`` inputs. ``CaseScore``,
``_score_prediction``, ``AblationCaseResult``, and ``RobustnessCaseResult`` are reused by
direct import (not reimplemented) because none of them embed a "development" label or are
otherwise dev-specific; ``DevelopmentCase``-typed dev orchestration functions
(``run_development_pilot``, ``run_llm_development_pilot``, ``run_ablations``,
``run_robustness``) are not reused directly because their result labels/docstrings are
hardcoded to "DEVELOPMENT ONLY" -- calling them for final execution would mislabel final
results, so this module provides its own thin orchestration loops around the same
underlying primitives instead.

PC-09 (``docs/protocol_deviations.md``): A1/A4/A6 and R1/R2/R3 run on the exact same
60-case final LLM subset as C1/C2/C4 -- there is no second ablation/robustness selector
anywhere in this module.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from statistics import mean

from kdaa.ontology import Ontology
from kdaa.providers.base import JSONProvider

from .ablations import (
    apply_a1_no_provenance_gate,
    apply_a4_flat_unit_representation,
    apply_a6_no_opportunity_specific_matching,
)
from .adapters import run_c0_s, run_c1, run_c2, run_c3, run_c4
from .analysis import PairedMetricSummary, summarize_paired
from .dev_pilot import CaseScore, _score_prediction
from .dev_pilot_llm import (
    AblationCaseResult,
    RobustnessCaseResult,
    _claim_label_signature,
    _jaccard,
)
from .fairness import validate_case_fairness
from .final_cases import FinalCase
from .leakage import validate_case_leakage
from .robustness import (
    r1_exact_duplicate,
    r1_source_equivalent_duplicate,
    r2_substantial_irrelevant_evidence,
    r3_ontology_surface_shift,
)
from .snapshot import build_input_snapshot
from .telemetry import AttemptStatus, ExperimentAttempt

FINAL_LABEL = "FINAL PAPER B EVALUATION -- FROZEN RESULTS"
FINAL_INTENDED_REPEATS = 3
FINAL_LLM_COMPARATORS = ("C1", "C2", "C4")

_PERTURBATIONS = {
    "R1_exact_duplicate": r1_exact_duplicate,
    "R1_source_equivalent_duplicate": r1_source_equivalent_duplicate,
    "R2_irrelevant_evidence": r2_substantial_irrelevant_evidence,
    "R3_ontology_surface_shift": r3_ontology_surface_shift,
}


def _snapshot_for(case: FinalCase):
    return build_input_snapshot(case.manifest.case_id, case.evidence_bundle, case.opportunity_catalog)


# --------------------------------------------------------------------------------------
# Final deterministic block: C0-S and C3 on all N=240
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FinalDeterministicResult:
    label: str
    n_cases: int
    as_of_date: str
    runtime_seconds: float
    case_scores: tuple[CaseScore, ...]


def run_final_deterministic_block(
    cases: list[FinalCase], *, as_of_date: date, ontology: Ontology | None = None
) -> FinalDeterministicResult:
    """C0-S and C3 on every case in ``cases`` (the caller passes all 240 final cases)."""
    ontology = ontology or Ontology.default()
    started = time.monotonic()
    case_scores: list[CaseScore] = []

    for case in cases:
        snapshot = _snapshot_for(case)
        validate_case_leakage(case.evidence_bundle, case.truth, snapshot)

        c0s_prediction = run_c0_s(snapshot, ontology)
        c3_prediction = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=as_of_date)
        validate_case_fairness(snapshot, c0s_prediction, snapshot, c3_prediction)

        case_scores.append(_score_prediction(case, c0s_prediction))
        case_scores.append(_score_prediction(case, c3_prediction))

    return FinalDeterministicResult(
        label=FINAL_LABEL,
        n_cases=len(cases),
        as_of_date=as_of_date.isoformat(),
        runtime_seconds=time.monotonic() - started,
        case_scores=tuple(case_scores),
    )


# --------------------------------------------------------------------------------------
# Final LLM block: C1/C2/C4 on the frozen 60-case subset, 3 intended repeats each
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FinalRepeatedCaseScore:
    """Superset of ``dev_pilot_llm.RepeatedCaseScore`` that additionally carries the mean
    unresolved/abstention rate -- required for the final study's E3 reporting rule
    (false-individualization, attribution coverage, and unresolved/abstention must always
    be reported together). The development-stage ``RepeatedCaseScore`` never aggregated
    this field; added here rather than editing that already-frozen Checkpoint B dataclass.
    """

    case_id: str
    comparator_id: str
    n_intended_repeats: int
    n_successful_repeats: int
    mean_concept_f1: float
    mean_unsupported_claim_rate: float | None
    mean_false_individualization_rate: float | None
    mean_attribution_coverage: float | None
    mean_unresolved_rate: float | None
    mean_ndcg_at_5: float
    per_repeat_status: tuple[str, ...]


def _score_final_attempts(case: FinalCase, attempts: list[ExperimentAttempt]) -> FinalRepeatedCaseScore:
    f1_values: list[float] = []
    ndcg_values: list[float] = []
    e2_values: list[float] = []
    far_values: list[float] = []
    coverage_values: list[float] = []
    unresolved_values: list[float] = []
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
            if score.unresolved_rate is not None:
                unresolved_values.append(score.unresolved_rate)
        else:
            # Failed intended run: WP1 failure policy (f1/ndcg_failed_run_value=0.0).
            f1_values.append(0.0)
            ndcg_values.append(0.0)

    return FinalRepeatedCaseScore(
        case_id=case.manifest.case_id,
        comparator_id=attempts[0].comparator_id if attempts else "",
        n_intended_repeats=len(attempts),
        n_successful_repeats=successful,
        mean_concept_f1=mean(f1_values) if f1_values else 0.0,
        mean_unsupported_claim_rate=mean(e2_values) if e2_values else None,
        mean_false_individualization_rate=mean(far_values) if far_values else None,
        mean_attribution_coverage=mean(coverage_values) if coverage_values else None,
        mean_unresolved_rate=mean(unresolved_values) if unresolved_values else None,
        mean_ndcg_at_5=mean(ndcg_values) if ndcg_values else 0.0,
        per_repeat_status=tuple(attempt.status.value for attempt in attempts),
    )


@dataclass(frozen=True)
class FinalLLMResult:
    label: str
    n_cases: int
    n_repeats: int
    runtime_seconds: float
    all_attempts: tuple[ExperimentAttempt, ...]
    repeated_scores: tuple[FinalRepeatedCaseScore, ...]

    @property
    def intended_calls(self) -> int:
        return self.n_cases * self.n_repeats * len(FINAL_LLM_COMPARATORS)


def run_final_llm_block(
    cases: list[FinalCase],
    *,
    provider_c1: JSONProvider,
    provider_c2: JSONProvider,
    provider_c4: JSONProvider,
    ontology: Ontology,
    as_of_date: date,
    n_repeats: int = FINAL_INTENDED_REPEATS,
) -> FinalLLMResult:
    """C1, C2, C4 for ``n_repeats`` intended repeats on every case in ``cases`` (the caller
    passes the frozen 60-case final LLM subset -- this function does not select it)."""
    started = time.monotonic()
    all_attempts: list[ExperimentAttempt] = []
    repeated_scores: list[FinalRepeatedCaseScore] = []

    for case in cases:
        snapshot = _snapshot_for(case)
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
            run_c4(case.evidence_bundle, snapshot, ontology, provider_c4, as_of_date=as_of_date, attempt_number=repeat)
            for repeat in range(1, n_repeats + 1)
        ]

        all_attempts.extend([*c1_attempts, *c2_attempts, *c4_attempts])
        repeated_scores.extend(
            [
                _score_final_attempts(case, c1_attempts),
                _score_final_attempts(case, c2_attempts),
                _score_final_attempts(case, c4_attempts),
            ]
        )

    return FinalLLMResult(
        label=FINAL_LABEL,
        n_cases=len(cases),
        n_repeats=n_repeats,
        runtime_seconds=time.monotonic() - started,
        all_attempts=tuple(all_attempts),
        repeated_scores=tuple(repeated_scores),
    )


# --------------------------------------------------------------------------------------
# Final ablations (A1/A4/A6) and robustness (R1/R2/R3): same frozen 60-case subset (PC-09)
# --------------------------------------------------------------------------------------


def run_final_ablations(cases: list[FinalCase], ontology: Ontology, *, as_of_date: date) -> list[AblationCaseResult]:
    """A1/A4/A6 against C3 on ``cases`` (PC-09: pass the frozen 60-case final LLM subset,
    not a second selection). Reuses the exact ablation transforms and scorer
    (``apply_a1_no_provenance_gate`` etc., ``_score_prediction``) unchanged."""
    results: list[AblationCaseResult] = []
    for case in cases:
        snapshot = _snapshot_for(case)
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


def run_final_robustness(cases: list[FinalCase], ontology: Ontology, *, as_of_date: date) -> list[RobustnessCaseResult]:
    """R1/R2/R3 against C3 on ``cases`` (PC-09: the frozen 60-case final LLM subset).
    Reuses the exact perturbation transforms unchanged (``r1_exact_duplicate`` etc.)."""
    results: list[RobustnessCaseResult] = []
    for case in cases:
        snapshot = _snapshot_for(case)
        baseline_prediction = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=as_of_date)
        baseline_score = _score_prediction(case, baseline_prediction)
        baseline_signature = _claim_label_signature(baseline_prediction)
        baseline_top = (
            baseline_prediction.ranked_opportunities[0].opportunity_id if baseline_prediction.ranked_opportunities else None
        )

        for perturbation_id, perturb in _PERTURBATIONS.items():
            perturbed_bundle = perturb(case.evidence_bundle)
            perturbed_snapshot = build_input_snapshot(case.manifest.case_id, perturbed_bundle, case.opportunity_catalog)
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


# --------------------------------------------------------------------------------------
# Final paired comparisons: reuses analysis.summarize_paired unchanged, no new statistics
# --------------------------------------------------------------------------------------

_PAIRED_METRICS: tuple[str, ...] = (
    "concept_f1",
    "unsupported_claim_rate",
    "false_individualization_rate",
    "attribution_coverage",
    "unresolved_rate",
    "ndcg_at_5",
)


def _metrics_from_case_score(score: CaseScore) -> dict[str, float | None]:
    return {
        "concept_f1": score.concept_f1,
        "unsupported_claim_rate": score.unsupported_claim_rate,
        "false_individualization_rate": score.false_individualization_rate,
        "attribution_coverage": score.attribution_coverage,
        "unresolved_rate": score.unresolved_rate,
        "ndcg_at_5": score.ndcg_at_5,
    }


def _metrics_from_repeated_score(score: FinalRepeatedCaseScore) -> dict[str, float | None]:
    return {
        "concept_f1": score.mean_concept_f1,
        "unsupported_claim_rate": score.mean_unsupported_claim_rate,
        "false_individualization_rate": score.mean_false_individualization_rate,
        "attribution_coverage": score.mean_attribution_coverage,
        "unresolved_rate": score.mean_unresolved_rate,
        "ndcg_at_5": score.mean_ndcg_at_5,
    }


def _paired_summary(
    metric: str,
    scores_a: dict[str, dict[str, float | None]],
    scores_b: dict[str, dict[str, float | None]],
    case_ids: list[str],
    *,
    seed: int,
) -> PairedMetricSummary:
    values_a: list[float] = []
    values_b: list[float] = []
    for case_id in case_ids:
        a = scores_a.get(case_id, {}).get(metric)
        b = scores_b.get(case_id, {}).get(metric)
        if a is None or b is None:
            continue
        values_a.append(a)
        values_b.append(b)
    return summarize_paired(metric, values_a, values_b, seed=seed)


def build_final_paired_comparisons(
    deterministic: FinalDeterministicResult,
    llm: FinalLLMResult,
    *,
    llm_subset_case_ids: tuple[str, ...],
    bootstrap_seed: int = 42,
) -> dict[str, dict[str, PairedMetricSummary]]:
    """Primary contrasts C3-vs-C0-S (all 240), C4-vs-C1/C4-vs-C2/C2-vs-C1 (the 60-case
    subset), and the secondary C4-vs-C3 trade-off (C3 restricted to the same 60-case
    subset, for paired comparability). No composite score is computed anywhere here."""
    det_by_comparator: dict[str, dict[str, dict[str, float | None]]] = {}
    for score in deterministic.case_scores:
        det_by_comparator.setdefault(score.comparator_id, {})[score.case_id] = _metrics_from_case_score(score)

    llm_by_comparator: dict[str, dict[str, dict[str, float | None]]] = {}
    for score in llm.repeated_scores:
        llm_by_comparator.setdefault(score.comparator_id, {})[score.case_id] = _metrics_from_repeated_score(score)

    all_case_ids = sorted(det_by_comparator.get("C3", {}))
    subset_ids = list(llm_subset_case_ids)

    def summaries(a: dict, b: dict, ids: list[str]) -> dict[str, PairedMetricSummary]:
        return {metric: _paired_summary(metric, a, b, ids, seed=bootstrap_seed) for metric in _PAIRED_METRICS}

    return {
        "C3_vs_C0-S": summaries(det_by_comparator.get("C3", {}), det_by_comparator.get("C0-S", {}), all_case_ids),
        "C4_vs_C1": summaries(llm_by_comparator.get("C4", {}), llm_by_comparator.get("C1", {}), subset_ids),
        "C4_vs_C2": summaries(llm_by_comparator.get("C4", {}), llm_by_comparator.get("C2", {}), subset_ids),
        "C2_vs_C1": summaries(llm_by_comparator.get("C2", {}), llm_by_comparator.get("C1", {}), subset_ids),
        "C4_vs_C3": summaries(llm_by_comparator.get("C4", {}), det_by_comparator.get("C3", {}), subset_ids),
    }


# --------------------------------------------------------------------------------------
# Output layout (directory structure only -- see scripts/run_paper_b_final.py for writers)
# --------------------------------------------------------------------------------------

FINAL_OUTPUT_SUBDIRS: tuple[str, ...] = (
    "manifests",
    "raw",
    "parsed",
    "validated",
    "metrics",
    "ablations",
    "robustness",
    "summary",
)


def ensure_final_output_layout(output_root) -> None:
    """Create the empty final-output directory skeleton (no result files). Callers decide
    the root -- this implementation step only ever passes a temporary directory."""
    from pathlib import Path

    root = Path(output_root)
    for subdir in FINAL_OUTPUT_SUBDIRS:
        (root / subdir).mkdir(parents=True, exist_ok=True)
