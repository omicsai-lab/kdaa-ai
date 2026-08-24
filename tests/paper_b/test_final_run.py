"""Final Paper B execution orchestration: validates kdaa.evaluation.paper_b.final_run
end-to-end with a small in-memory case set and a fake provider -- never real final data,
never a live API call. See tests/paper_b/test_final_cases.py for the data-generation
layer this module consumes."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from kdaa.evaluation.paper_b import dev_pilot, dev_pilot_llm
from kdaa.evaluation.paper_b.ablations import (
    apply_a1_no_provenance_gate,
    apply_a4_flat_unit_representation,
    apply_a6_no_opportunity_specific_matching,
)
from kdaa.evaluation.paper_b.adapters.fake_provider import always_succeeding_provider
from kdaa.evaluation.paper_b.boundary import find_truth_leakage
from kdaa.evaluation.paper_b.final_cases import (
    generate_final_challenge_case,
    generate_final_core_case,
)
from kdaa.evaluation.paper_b.final_llm_subset import select_final_llm_subset
from kdaa.evaluation.paper_b.final_run import (
    FINAL_OUTPUT_SUBDIRS,
    build_final_paired_comparisons,
    ensure_final_output_layout,
    run_final_ablations,
    run_final_deterministic_block,
    run_final_llm_block,
    run_final_robustness,
)
from kdaa.evaluation.paper_b.robustness import (
    r1_exact_duplicate,
    r1_source_equivalent_duplicate,
    r2_substantial_irrelevant_evidence,
    r3_ontology_surface_shift,
)
from kdaa.ontology import Ontology

REPO_ROOT = Path(__file__).resolve().parents[2]
_AS_OF_DATE = date(2026, 6, 1)
_FAKE_OPPORTUNITY_IDS = [
    "opp-repository",
    "opp-living-document",
    "opp-knowledge-base",
    "opp-deployable-product",
    "opp-public-content",
    "opp-grant-proposal",
    "opp-benchmark-dataset",
    "opp-training-course",
    "opp-consulting-service",
    "opp-methods-paper",
]


def _fake_provider():
    return always_succeeding_provider(
        concepts=[{"label": "Agentic AI", "ownership": "focal_unit"}], ranked_opportunity_ids=_FAKE_OPPORTUNITY_IDS
    )


def _small_core_set(n: int = 6) -> list:
    return [generate_final_core_case(i) for i in range(n)]


def _small_challenge_set(n: int = 4) -> list:
    return [generate_final_challenge_case(i) for i in range(n)]


# --------------------------------------------------------------------------------------
# 1. Final runner accepts FinalCase
# --------------------------------------------------------------------------------------


def test_final_deterministic_block_accepts_final_case_objects() -> None:
    from kdaa.evaluation.paper_b.final_cases import FinalCase

    cases = _small_core_set(2)
    assert all(isinstance(c, FinalCase) for c in cases)
    result = run_final_deterministic_block(cases, as_of_date=_AS_OF_DATE)
    assert result.n_cases == 2


# --------------------------------------------------------------------------------------
# 2. Full deterministic block covers all cases handed to it (proxy for "all 240" -- a
#    small set here, exercised at real N=240 scale via the CLI script's own dry-run print)
# --------------------------------------------------------------------------------------


def test_deterministic_block_scores_c0s_and_c3_for_every_case() -> None:
    cases = _small_core_set(3) + _small_challenge_set(2)
    result = run_final_deterministic_block(cases, as_of_date=_AS_OF_DATE)
    assert result.n_cases == 5
    assert len(result.case_scores) == 2 * 5  # C0-S + C3 per case
    comparators = {s.comparator_id for s in result.case_scores}
    assert comparators == {"C0-S", "C3"}
    scored_case_ids = {s.case_id for s in result.case_scores}
    assert scored_case_ids == {c.manifest.case_id for c in cases}


def test_deterministic_block_label_is_final_not_development() -> None:
    result = run_final_deterministic_block(_small_core_set(1), as_of_date=_AS_OF_DATE)
    assert "FINAL" in result.label
    assert "DEVELOPMENT" not in result.label


# --------------------------------------------------------------------------------------
# 3-4. LLM block uses exactly the frozen 60-case subset; intended calls = 540 at real N
# --------------------------------------------------------------------------------------


def test_llm_block_runs_c1_c2_c4_with_three_repeats_on_given_cases() -> None:
    ontology = Ontology.default()
    cases = _small_core_set(2)
    provider = _fake_provider()
    result = run_final_llm_block(
        cases, provider_c1=provider, provider_c2=provider, provider_c4=provider, ontology=ontology, as_of_date=_AS_OF_DATE
    )
    assert result.n_cases == 2
    assert result.n_repeats == 3
    assert len(result.all_attempts) == 2 * 3 * 3  # cases x repeats x comparators
    comparators = {a.comparator_id for a in result.all_attempts}
    assert comparators == {"C1", "C2", "C4"}


def test_intended_calls_formula_equals_540_at_real_final_subset_size() -> None:
    # The formula itself (not tied to a specific run) -- confirms the arithmetic the CLI
    # script relies on for its real-N=60 sanity print.
    from kdaa.evaluation.paper_b.final_run import FINAL_LLM_COMPARATORS

    n_subset, n_repeats = 60, 3
    assert n_subset * n_repeats * len(FINAL_LLM_COMPARATORS) == 540


def test_llm_block_uses_exactly_the_cases_it_is_given_not_a_different_selection() -> None:
    ontology = Ontology.default()
    dataset_core = _small_core_set(4)
    subset = dataset_core[:2]  # simulate "the frozen subset" being a strict subset
    provider = _fake_provider()
    result = run_final_llm_block(
        subset, provider_c1=provider, provider_c2=provider, provider_c4=provider, ontology=ontology, as_of_date=_AS_OF_DATE
    )
    scored_ids = {a.case_id for a in result.all_attempts}
    assert scored_ids == {c.manifest.case_id for c in subset}
    assert scored_ids != {c.manifest.case_id for c in dataset_core}  # did not silently use all 4


# --------------------------------------------------------------------------------------
# 5-6. A1/A4/A6 and R1/R2/R3 use exactly the frozen 60-case subset (PC-09) -- no second
# selector; here proven at small scale that ablations/robustness receive exactly what
# they're handed, matching whatever the LLM block also received.
# --------------------------------------------------------------------------------------


def test_ablations_and_robustness_run_on_exactly_the_same_case_ids_as_the_llm_block() -> None:
    ontology = Ontology.default()
    cases = _small_core_set(2) + _small_challenge_set(2)
    provider = _fake_provider()

    llm_result = run_final_llm_block(
        cases, provider_c1=provider, provider_c2=provider, provider_c4=provider, ontology=ontology, as_of_date=_AS_OF_DATE
    )
    ablation_results = run_final_ablations(cases, ontology, as_of_date=_AS_OF_DATE)
    robustness_results = run_final_robustness(cases, ontology, as_of_date=_AS_OF_DATE)

    llm_case_ids = {a.case_id for a in llm_result.all_attempts}
    ablation_case_ids = {r.case_id for r in ablation_results}
    robustness_case_ids = {r.case_id for r in robustness_results}
    expected = {c.manifest.case_id for c in cases}

    assert llm_case_ids == ablation_case_ids == robustness_case_ids == expected


def test_final_experiment_lock_records_pc09_subset_reuse() -> None:
    import yaml

    lock = yaml.safe_load((REPO_ROOT / "configs" / "paper_b" / "final_experiment_lock.yaml").read_text())
    assert lock["ablations"]["subset"] == "reuses_frozen_final_llm_subset"
    assert lock["robustness"]["subset"] == "reuses_frozen_final_llm_subset"
    assert lock["ablations"]["subset_n"] == 60
    assert lock["robustness"]["subset_n"] == 60
    assert set(lock["final_llm_subset"]["also_used_for"]) == {"A1", "A4", "A6", "R1", "R2", "R3"}


def test_ablation_count_is_three_per_case() -> None:
    ontology = Ontology.default()
    cases = _small_core_set(3)
    results = run_final_ablations(cases, ontology, as_of_date=_AS_OF_DATE)
    assert len(results) == 3 * 3  # A1, A4, A6 per case
    assert {r.ablation_id for r in results} == {"A1", "A4", "A6"}


def test_robustness_count_matches_the_frozen_perturbation_set() -> None:
    ontology = Ontology.default()
    cases = _small_core_set(3)
    results = run_final_robustness(cases, ontology, as_of_date=_AS_OF_DATE)
    assert len(results) == 3 * 4  # 2 R1 variants + R2 + R3, per case (unchanged Checkpoint B set)
    assert {r.perturbation_id for r in results} == {
        "R1_exact_duplicate",
        "R1_source_equivalent_duplicate",
        "R2_irrelevant_evidence",
        "R3_ontology_surface_shift",
    }


# --------------------------------------------------------------------------------------
# 7. Final scorers/transforms are reused, not redefined
# --------------------------------------------------------------------------------------


def test_final_run_reuses_dev_pilot_case_score_and_scorer_by_identity() -> None:
    from kdaa.evaluation.paper_b import final_run

    assert final_run.CaseScore is dev_pilot.CaseScore
    assert final_run._score_prediction is dev_pilot._score_prediction


def test_final_run_reuses_ablation_and_robustness_result_types_by_identity() -> None:
    from kdaa.evaluation.paper_b import final_run

    assert final_run.AblationCaseResult is dev_pilot_llm.AblationCaseResult
    assert final_run.RobustnessCaseResult is dev_pilot_llm.RobustnessCaseResult


def test_final_run_reuses_ablation_transforms_and_perturbations_by_identity() -> None:
    from kdaa.evaluation.paper_b import ablations as ablations_module
    from kdaa.evaluation.paper_b import final_run
    from kdaa.evaluation.paper_b import robustness as robustness_module

    assert final_run.apply_a1_no_provenance_gate is ablations_module.apply_a1_no_provenance_gate is apply_a1_no_provenance_gate
    assert final_run.apply_a4_flat_unit_representation is ablations_module.apply_a4_flat_unit_representation is apply_a4_flat_unit_representation
    assert (
        final_run.apply_a6_no_opportunity_specific_matching
        is ablations_module.apply_a6_no_opportunity_specific_matching
        is apply_a6_no_opportunity_specific_matching
    )
    assert final_run.r1_exact_duplicate is robustness_module.r1_exact_duplicate is r1_exact_duplicate
    assert final_run.r1_source_equivalent_duplicate is robustness_module.r1_source_equivalent_duplicate is r1_source_equivalent_duplicate
    assert final_run.r2_substantial_irrelevant_evidence is robustness_module.r2_substantial_irrelevant_evidence is r2_substantial_irrelevant_evidence
    assert final_run.r3_ontology_surface_shift is robustness_module.r3_ontology_surface_shift is r3_ontology_surface_shift


def test_final_run_reuses_analysis_summarize_paired_by_identity() -> None:
    from kdaa.evaluation.paper_b import analysis, final_run

    assert final_run.summarize_paired is analysis.summarize_paired


def test_e3_metrics_always_reported_together() -> None:
    ontology = Ontology.default()
    cases = _small_core_set(2)
    provider = _fake_provider()
    result = run_final_llm_block(
        cases, provider_c1=provider, provider_c2=provider, provider_c4=provider, ontology=ontology, as_of_date=_AS_OF_DATE
    )
    for score in result.repeated_scores:
        # All three E3 fields exist on every record (value may be None if inapplicable,
        # but the field itself -- unlike dev_pilot_llm.RepeatedCaseScore -- always exists).
        assert hasattr(score, "mean_false_individualization_rate")
        assert hasattr(score, "mean_attribution_coverage")
        assert hasattr(score, "mean_unresolved_rate")


# --------------------------------------------------------------------------------------
# 8. Fake-provider dry run succeeds end-to-end, including paired comparisons
# --------------------------------------------------------------------------------------


def test_full_dry_run_with_fake_provider_succeeds_and_builds_comparisons() -> None:
    ontology = Ontology.default()
    core_cases = _small_core_set(6)
    challenge_cases = _small_challenge_set(4)
    all_cases = core_cases + challenge_cases
    subset = select_final_llm_subset(core_cases, challenge_cases, n_core=4, n_per_challenge_category=0)
    # n_per_challenge_category=0 keeps this fast; use core-only subset ids for this test.
    subset_cases = [c for c in core_cases if c.manifest.case_id in set(subset.core_case_ids)]

    deterministic = run_final_deterministic_block(all_cases, as_of_date=_AS_OF_DATE, ontology=ontology)
    provider = _fake_provider()
    llm = run_final_llm_block(
        subset_cases, provider_c1=provider, provider_c2=provider, provider_c4=provider, ontology=ontology, as_of_date=_AS_OF_DATE
    )
    comparisons = build_final_paired_comparisons(
        deterministic, llm, llm_subset_case_ids=tuple(c.manifest.case_id for c in subset_cases)
    )
    assert set(comparisons) == {"C3_vs_C0-S", "C4_vs_C1", "C4_vs_C2", "C2_vs_C1", "C4_vs_C3"}
    for contrast in comparisons.values():
        assert set(contrast) == {
            "concept_f1",
            "unsupported_claim_rate",
            "false_individualization_rate",
            "attribution_coverage",
            "unresolved_rate",
            "ndcg_at_5",
        }


def test_no_composite_score_is_ever_computed() -> None:
    # Behavioral check (not a source-text scan, which false-positives on this module's own
    # docstring explaining that no composite score is computed): the FinalDeterministicResult
    # / FinalLLMResult dataclasses and the paired-comparisons dict never carry a
    # composite/overall field or contrast key.
    from dataclasses import fields

    from kdaa.evaluation.paper_b.final_run import FinalDeterministicResult, FinalLLMResult

    for cls in (FinalDeterministicResult, FinalLLMResult):
        field_names = {f.name.lower() for f in fields(cls)}
        assert not any("composite" in name or "overall" in name for name in field_names)

    ontology = Ontology.default()
    cases = _small_core_set(2)
    deterministic = run_final_deterministic_block(cases, as_of_date=_AS_OF_DATE, ontology=ontology)
    provider = _fake_provider()
    llm = run_final_llm_block(
        cases, provider_c1=provider, provider_c2=provider, provider_c4=provider, ontology=ontology, as_of_date=_AS_OF_DATE
    )
    comparisons = build_final_paired_comparisons(
        deterministic, llm, llm_subset_case_ids=tuple(c.manifest.case_id for c in cases)
    )
    assert not any("composite" in key.lower() or "overall" in key.lower() for key in comparisons)


# --------------------------------------------------------------------------------------
# 9. No final-data paths are created
# --------------------------------------------------------------------------------------


def test_running_the_final_blocks_creates_no_real_final_data_directory() -> None:
    final_evidence_dir = REPO_ROOT / "data" / "synthetic" / "final_evidence"
    final_truth_dir = REPO_ROOT / "data" / "synthetic" / "final_truth"
    assert not final_evidence_dir.exists()
    assert not final_truth_dir.exists()

    ontology = Ontology.default()
    cases = _small_core_set(2)
    run_final_deterministic_block(cases, as_of_date=_AS_OF_DATE, ontology=ontology)
    run_final_ablations(cases, ontology, as_of_date=_AS_OF_DATE)
    run_final_robustness(cases, ontology, as_of_date=_AS_OF_DATE)

    assert not final_evidence_dir.exists()
    assert not final_truth_dir.exists()


def test_ensure_final_output_layout_only_touches_the_given_root(tmp_path) -> None:
    ensure_final_output_layout(tmp_path)
    for subdir in FINAL_OUTPUT_SUBDIRS:
        assert (tmp_path / subdir).is_dir()
        assert list((tmp_path / subdir).iterdir()) == []  # empty -- no fake results written

    real_final_results_dir = REPO_ROOT / "results" / "paper_b" / "final"
    assert not real_final_results_dir.exists()


def test_real_results_paper_b_final_directory_does_not_exist_yet() -> None:
    assert not (REPO_ROOT / "results" / "paper_b" / "final").exists()


# --------------------------------------------------------------------------------------
# 10. Truth/inference isolation remains clean
# --------------------------------------------------------------------------------------


def test_truth_inference_boundary_still_clean_after_adding_final_run() -> None:
    assert find_truth_leakage() == {}


def test_final_run_module_never_imports_truth_or_opportunity_truth() -> None:
    import ast
    import inspect

    from kdaa.evaluation.paper_b import final_run

    tree = ast.parse(inspect.getsource(final_run))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module not in {"truth", "opportunity_truth"}
            assert not (node.module or "").endswith((".truth", ".opportunity_truth"))
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "opportunity_truth" not in alias.name
                assert not alias.name.endswith(".truth")
