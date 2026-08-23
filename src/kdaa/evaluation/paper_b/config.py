"""Loader and strict schema for the frozen Paper B experiment lock.

Source of truth: ``configs/paper_b/experiment_lock.yaml``, copied byte-for-byte from the
approved KDAA-PB-KBS-EXP-001 v1.0 freeze under WP0 (see docs/paper_b_repo_baseline.md for
the hash record). This module only loads and validates that file. Every field mirrors the
YAML exactly, using strict nested models (``extra="forbid"``) rather than a generic
``dict[str, Any]``, so a typo'd key, a missing frozen value, or an unexpected addition is
rejected at load time instead of silently ignored. This module must never substitute a
default for a missing frozen value or otherwise change the lock's scientific content.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .base import StrictEvalModel
from .hashing import content_hash

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_EXPERIMENT_LOCK_PATH = REPO_ROOT / "configs" / "paper_b" / "experiment_lock.yaml"


class ResearchQuestionsLock(StrictEvalModel):
    RQ1: str
    RQ2: str
    RQ3: str


class DevelopmentDataLock(StrictEvalModel):
    n_min: int
    reported_as_final: bool
    disjoint_from_final: bool


class CoreFactorialLock(StrictEvalModel):
    unit_type: list[str]
    evidence_density: list[str]
    domain_breadth: list[str]
    attribution_regime: list[str]
    replicates_per_cell: int


class FinalSyntheticDataLock(StrictEvalModel):
    total_n: int
    core_n: int
    challenge_n: int
    core_factorial: CoreFactorialLock
    challenge_categories: list[str]


class LLMSubsetLock(StrictEvalModel):
    n: int
    core_n: int
    challenge_n: int
    intended_repeats: int


class AblationSubsetLock(StrictEvalModel):
    n: int
    core_n: int
    challenge_n: int
    intended_repeats_when_stochastic: int


class ResourceMatchedSubsetLock(StrictEvalModel):
    n: int
    intended_repeats: int


class ModelPromptRobustnessSubsetLock(StrictEvalModel):
    n_min: int


class AuthorControlledCaseLock(StrictEvalModel):
    allowed: bool
    included_in_aggregate: bool


class PublicCasesLock(StrictEvalModel):
    independent_n: int
    approximate_individual_n: int
    approximate_collective_n: int
    minimum_domains: int
    author_controlled_case: AuthorControlledCaseLock


class DataLock(StrictEvalModel):
    development: DevelopmentDataLock
    final_synthetic: FinalSyntheticDataLock
    llm_subset: LLMSubsetLock
    ablation_subset: AblationSubsetLock
    resource_matched_subset: ResourceMatchedSubsetLock
    model_prompt_robustness_subset: ModelPromptRobustnessSubsetLock
    public_cases: PublicCasesLock


class ComparatorLock(StrictEvalModel):
    name: str
    role: str
    max_asset_candidates: int | None = None
    opportunity_candidates: int | None = None
    tuning_data: str | None = None
    kdaa_design_knowledge: bool | None = None
    evidence_ids_required: bool | None = None


class ComparatorsLock(StrictEvalModel):
    C0_L: ComparatorLock
    C0_S: ComparatorLock
    C1: ComparatorLock
    C2: ComparatorLock
    C3: ComparatorLock
    C4: ComparatorLock
    C4_R: ComparatorLock


class EndpointLock(StrictEvalModel):
    name: str
    direction: str


class PrimaryEndpointsLock(StrictEvalModel):
    E1: EndpointLock
    E2: EndpointLock
    E3: EndpointLock
    E4: EndpointLock


class HardInvariantsLock(StrictEvalModel):
    provenance_completeness_after_validation: float
    invalid_trace_reference_rate_after_validation: float
    automatic_confirmation_without_calibration: float
    illegal_state_transition_acceptance_rate: float
    sensitive_trace_remote_transmission_default: float
    deterministic_exact_reproducibility: float
    opportunities_with_asset_reference: float
    public_report_warning_completeness: float


class MainAblationsLock(StrictEvalModel):
    A1: str
    A2: str
    A3: str
    A4: str
    A6: str
    A7: str


class A9Lock(StrictEvalModel):
    name: str
    governance_stress_only: bool
    normal_execution_mode: bool


class SupplementaryAblationsLock(StrictEvalModel):
    A5: str
    A8: str
    A9: A9Lock


class PracticalEffectReferenceLock(StrictEvalModel):
    f1_absolute: float
    ndcg_at_5_absolute: float
    unsupported_claim_rate_absolute: float
    false_individualization_rate_absolute: float


class StatisticsLock(StrictEvalModel):
    unit_of_analysis: str
    bootstrap_resamples: int
    bootstrap_type: str
    llm_case_summary: str
    best_of_n_selection_allowed: bool
    primary_test_adjustment: str
    secondary_test_adjustment: str
    practical_effect_reference: PracticalEffectReferenceLock


class FailurePolicyLock(StrictEvalModel):
    max_automatic_retries: int
    preserve_all_attempts: bool
    f1_failed_run_value: float
    ndcg_failed_run_value: float
    rate_endpoint_worst_case_sensitivity: bool
    successful_run_only_primary_analysis: bool


class FairnessLock(StrictEvalModel):
    same_model_snapshot_for_C1_C2_C4_C4R: bool
    same_semantic_evidence_content: bool
    same_opportunity_catalog: bool
    max_asset_candidates: int
    max_ranked_opportunities: int
    fixed_case_input_order: bool
    output_adapter_may_add_content: bool
    model_shopping_on_final_results: bool
    report_calls_tokens_latency_cost: bool


class LeakageControlLock(StrictEvalModel):
    truth_outside_model_visible_bundle: bool
    truth_hash_before_final_runs: bool
    inference_before_scoring_access: bool
    final_case_replacement_allowed: bool
    final_threshold_tuning_allowed: bool
    prompt_truth_token_scan: bool


class PublicCaseInterpretationLock(StrictEvalModel):
    proves_asset_truth: bool
    proves_human_usefulness: bool
    held_out_anchor_is_complete_ground_truth: bool
    cross_person_ranking_allowed: bool
    high_stakes_use_allowed: bool


class ReproducibilityLock(StrictEvalModel):
    top_level_command: str
    programmatic_tables_and_figures: bool
    raw_parsed_validated_outputs_retained: bool
    clean_environment_nonpaid_reproduction: bool
    protocol_deviations_file_required: bool


class ExperimentLock(StrictEvalModel):
    document_id: str
    version: str
    status: str
    freeze_date: str
    target_journal: str
    fallback_journal: str
    research_questions: ResearchQuestionsLock
    data: DataLock
    comparators: ComparatorsLock
    primary_contrasts: list[list[str]]
    secondary_contrasts: list[list[str]]
    primary_endpoints: PrimaryEndpointsLock
    hard_invariants: HardInvariantsLock
    main_ablations: MainAblationsLock
    supplementary_ablations: SupplementaryAblationsLock
    perturbation_families: list[str]
    statistics: StatisticsLock
    failure_policy: FailurePolicyLock
    fairness: FairnessLock
    leakage_control: LeakageControlLock
    public_case_interpretation: PublicCaseInterpretationLock
    reproducibility: ReproducibilityLock

    def canonical_hash(self) -> str:
        return content_hash(self)


def load_experiment_lock(path: str | Path | None = None) -> ExperimentLock:
    """Load and strictly validate the Paper B experiment lock.

    Raises ``FileNotFoundError`` if the file is missing and ``pydantic.ValidationError`` (via
    ``model_validate``) if its content does not exactly match the frozen schema.
    """
    resolved = Path(path) if path is not None else DEFAULT_EXPERIMENT_LOCK_PATH
    if not resolved.is_file():
        raise FileNotFoundError(f"Paper B experiment lock not found at {resolved}")
    with resolved.open(encoding="utf-8") as handle:
        payload: Any = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Paper B experiment lock at {resolved} did not parse to a mapping")
    return ExperimentLock.model_validate(payload)
