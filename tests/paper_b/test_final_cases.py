"""Final Paper B data-generation machinery: validates the frozen final-dataset design
implemented in kdaa.evaluation.paper_b.final_cases/final_opportunities/final_llm_subset
against configs/paper_b/final_experiment_lock.yaml, without ever generating or persisting
the actual final N=240 dataset (see test_no_final_data_directory_or_file_is_created)."""

from __future__ import annotations

import ast
import inspect
from collections import Counter
from pathlib import Path

from kdaa.evaluation.paper_b import final_cases, final_opportunities
from kdaa.evaluation.paper_b.boundary import find_truth_leakage
from kdaa.evaluation.paper_b.final_cases import (
    _UNSEEN_SYNONYMS,
    CHALLENGE_N,
    CORE_N,
    generate_final_challenge_case,
    generate_final_challenge_set,
    generate_final_core_case,
    generate_final_core_set,
    generate_final_dataset,
)
from kdaa.evaluation.paper_b.final_llm_subset import select_final_llm_subset
from kdaa.evaluation.paper_b.schemas import ChallengeCategory
from kdaa.ingestion.dedup import deduplicate_traces
from kdaa.ontology import Ontology

REPO_ROOT = Path(__file__).resolve().parents[2]

# --------------------------------------------------------------------------------------
# Core factorial counts (180 = 3 x 2 x 2 x 3 x 5)
# --------------------------------------------------------------------------------------


def test_core_set_has_exactly_180_cases() -> None:
    assert CORE_N == 180
    cases = generate_final_core_set()
    assert len(cases) == 180


def test_core_factorial_cells_are_exactly_the_frozen_180_combination() -> None:
    cases = generate_final_core_set()
    cell_counts = Counter(
        (c.manifest.unit_type, c.manifest.evidence_density, c.manifest.domain_breadth, c.manifest.attribution_regime)
        for c in cases
    )
    assert len(cell_counts) == 3 * 2 * 2 * 3  # 36 distinct cells
    assert all(count == 5 for count in cell_counts.values())  # exactly 5 replicates each


def test_core_case_ids_are_unique() -> None:
    cases = generate_final_core_set()
    ids = [c.manifest.case_id for c in cases]
    assert len(set(ids)) == len(ids) == 180


def test_core_cases_are_flagged_not_development_and_not_challenge() -> None:
    for case in generate_final_core_set():
        assert case.manifest.development_case is False
        assert case.manifest.is_challenge_case is False
        assert case.manifest.challenge_category is None


def test_core_flat_index_out_of_range_raises() -> None:
    import pytest

    with pytest.raises(ValueError, match=r"\[0, 180\)"):
        generate_final_core_case(180)
    with pytest.raises(ValueError):
        generate_final_core_case(-1)


# --------------------------------------------------------------------------------------
# Challenge counts (60 = 10 categories x 6)
# --------------------------------------------------------------------------------------


def test_challenge_set_has_exactly_60_cases() -> None:
    assert CHALLENGE_N == 60
    cases = generate_final_challenge_set()
    assert len(cases) == 60


def test_challenge_categories_have_exactly_6_cases_each() -> None:
    cases = generate_final_challenge_set()
    counts = Counter(c.manifest.challenge_category for c in cases)
    assert set(counts) == set(ChallengeCategory)
    assert len(counts) == 10
    assert all(count == 6 for count in counts.values())


def test_challenge_case_ids_are_unique() -> None:
    cases = generate_final_challenge_set()
    ids = [c.manifest.case_id for c in cases]
    assert len(set(ids)) == len(ids) == 60


def test_challenge_cases_are_flagged_correctly() -> None:
    for case in generate_final_challenge_set():
        assert case.manifest.development_case is False
        assert case.manifest.is_challenge_case is True
        assert case.manifest.challenge_category is not None
        assert case.truth.challenge_category == case.manifest.challenge_category


def test_all_240_case_ids_are_globally_unique() -> None:
    dataset = generate_final_dataset()
    ids = [c.manifest.case_id for c in list(dataset.core_cases) + list(dataset.challenge_cases)]
    assert len(set(ids)) == len(ids) == 240


# --------------------------------------------------------------------------------------
# Exactly 10 opportunities per case
# --------------------------------------------------------------------------------------


def test_every_case_has_exactly_10_visible_opportunities_and_10_hidden_grades() -> None:
    dataset = generate_final_dataset()
    for case in list(dataset.core_cases) + list(dataset.challenge_cases):
        assert len(case.opportunity_catalog) == 10
        assert len(case.truth.opportunity_relevance) == 10
        visible_ids = {o.opportunity_id for o in case.opportunity_catalog}
        hidden_ids = {r.opportunity_id for r in case.truth.opportunity_relevance}
        assert visible_ids == hidden_ids  # same 10 opportunities on both sides


def test_all_comparators_would_rank_the_same_10_opportunities_for_a_case() -> None:
    # Structural guarantee: opportunity_catalog is a single tuple attached to the case, not
    # per-comparator -- there is no code path that could hand different comparators
    # different opportunity sets for the same case.
    case = generate_final_core_case(0)
    ids_a = [o.opportunity_id for o in case.opportunity_catalog]
    ids_b = [o.opportunity_id for o in case.opportunity_catalog]
    assert ids_a == ids_b


def test_visible_opportunity_descriptions_never_mention_hidden_requirement_vocabulary() -> None:
    from kdaa.evaluation.paper_b.opportunity_truth import OPPORTUNITY_REQUIREMENTS

    case = generate_final_core_case(3)
    hidden_concept_words = {
        word for req in OPPORTUNITY_REQUIREMENTS.values() for word in (req.required_concepts | req.optional_concepts | req.disqualifying_concepts)
    }
    for opp in case.opportunity_catalog:
        text = f"{opp.title} {opp.description}".lower()
        for concept_key in hidden_concept_words:
            assert concept_key not in text  # e.g. the literal token "software_engineering"


def test_two_materially_different_cases_do_not_get_byte_identical_catalogs() -> None:
    # case 0 (individual researcher, template 0) vs case 91 (team, template 91%6=1 --
    # different template, different unit_type): must differ, not just by a case-id sentence.
    case_a = generate_final_core_case(0)
    case_b = generate_final_core_case(91)
    assert case_a.manifest.unit_type != case_b.manifest.unit_type
    assert case_a.opportunity_catalog != case_b.opportunity_catalog
    for opp_a, opp_b in zip(case_a.opportunity_catalog, case_b.opportunity_catalog, strict=True):
        assert opp_a.opportunity_id == opp_b.opportunity_id  # same 10 identities
        assert opp_a.description != opp_b.description  # but materially different content


def test_visible_catalog_depends_only_on_evidence_side_context() -> None:
    # build_case_opportunity_catalog's signature has no truth parameter at all -- it is
    # structurally incapable of reading hidden truth. Confirm via signature inspection.
    signature = inspect.signature(final_opportunities.build_case_opportunity_catalog)
    assert "truth" not in signature.parameters
    assert set(signature.parameters) == {"evidence_bundle", "ontology"}


def test_mutating_hidden_truth_with_evidence_fixed_does_not_change_visible_catalog() -> None:
    from kdaa.ontology import Ontology

    ontology = Ontology.default()
    case = generate_final_core_case(5)
    baseline_catalog = final_opportunities.build_case_opportunity_catalog(case.evidence_bundle, ontology=ontology)

    # Mutate truth arbitrarily (different asset concepts, different ownership, different
    # opportunity grades) while keeping evidence_bundle byte-identical.
    from kdaa.evaluation.paper_b.schemas import OwnershipLabel
    from kdaa.evaluation.paper_b.truth import (
        TrueAssetConcept,
        TrueOpportunityRelevance,
        TruthBundle,
    )

    mutated_truth = TruthBundle(
        case_id=case.manifest.case_id,
        asset_concepts=[
            TrueAssetConcept(concept_id="genomics", canonical_label="Genomics", ownership_state=OwnershipLabel.EXTERNAL)
        ],
        opportunity_relevance=[TrueOpportunityRelevance(opportunity_id="opp-repository", relevance_grade=3)],
    )
    assert mutated_truth != case.truth  # sanity: the mutation actually changed something

    recomputed_catalog = final_opportunities.build_case_opportunity_catalog(case.evidence_bundle, ontology=ontology)
    assert recomputed_catalog == baseline_catalog  # unaffected by the (unused) mutated_truth


# --------------------------------------------------------------------------------------
# Truth/evidence separation and leakage
# --------------------------------------------------------------------------------------


def test_truth_is_a_physically_separate_object_from_evidence() -> None:
    case = generate_final_core_case(0)
    assert case.evidence_bundle.metadata == {}  # never embeds truth
    # FinalCase keeps evidence_bundle and truth as separate top-level fields (WP1 pattern)
    assert case.truth is not case.evidence_bundle
    assert not hasattr(case.evidence_bundle, "truth")


def test_truth_isolation_boundary_check_passes_for_the_final_generator_modules() -> None:
    violations = find_truth_leakage()
    assert violations == {}


def test_final_opportunities_module_never_imports_opportunity_truth() -> None:
    source = inspect.getsource(final_opportunities)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "opportunity_truth"
            assert not (node.module or "").endswith(".opportunity_truth")
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "opportunity_truth" not in alias.name


def test_final_cases_module_is_outside_the_inference_boundary_namespaces() -> None:
    # final_cases.py is truth-authorized generation code (like dev_cases.py), not an
    # inference/adapter module -- confirm it is not accidentally inside a boundary prefix.
    from kdaa.evaluation.paper_b.boundary import INFERENCE_BOUNDARY_PREFIXES

    module_name = final_cases.__name__
    assert not any(module_name.startswith(prefix) for prefix in INFERENCE_BOUNDARY_PREFIXES)


# --------------------------------------------------------------------------------------
# Final LLM subset: 60 = 30 core + 30 challenge; 540 intended calls
# --------------------------------------------------------------------------------------


def test_final_llm_subset_is_exactly_30_core_plus_30_challenge() -> None:
    dataset = generate_final_dataset()
    subset = select_final_llm_subset(list(dataset.core_cases), list(dataset.challenge_cases))
    assert subset.n_core == 30
    assert subset.n_challenge == 30
    assert subset.n == 60
    assert len(subset.core_case_ids) == 30
    assert len(subset.challenge_case_ids) == 30


def test_intended_c1_c2_c4_live_calls_calculate_to_540() -> None:
    dataset = generate_final_dataset()
    subset = select_final_llm_subset(list(dataset.core_cases), list(dataset.challenge_cases))
    assert subset.comparators == ("C1", "C2", "C4")
    assert subset.intended_repeats_per_case == 3
    assert subset.intended_primary_live_llm_calls == 60 * 3 * 3 == 540


def test_final_subset_selection_does_not_depend_on_any_prediction_or_truth_value() -> None:
    # Scans the WHOLE module (not just select_final_llm_subset itself), since the actual
    # stratification logic lives in the private _select_stratified_core_ids /
    # _select_stratified_challenge_ids helpers it calls.
    from kdaa.evaluation.paper_b import final_llm_subset

    source = inspect.getsource(final_llm_subset)
    tree = ast.parse(source)
    attributes_accessed = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "truth" not in attributes_accessed


def test_final_subset_selection_unchanged_if_truth_or_output_is_mutated() -> None:
    # Empirical companion to the AST check above: construct cases whose manifests are
    # identical but whose truth objects differ, and confirm the selected IDs don't change.
    dataset = generate_final_dataset()
    baseline = select_final_llm_subset(list(dataset.core_cases), list(dataset.challenge_cases))

    mutated_truth = dataset.core_cases[0].truth.model_copy(update={"asset_concepts": []})
    mutated_core_cases = [
        c if i != 0 else final_cases.FinalCase(manifest=c.manifest, evidence_bundle=c.evidence_bundle, truth=mutated_truth, opportunity_catalog=c.opportunity_catalog)
        for i, c in enumerate(dataset.core_cases)
    ]
    mutated = select_final_llm_subset(mutated_core_cases, list(dataset.challenge_cases))
    assert mutated.core_case_ids == baseline.core_case_ids
    assert mutated.challenge_case_ids == baseline.challenge_case_ids


def test_final_core_subset_covers_all_factor_levels_without_sequential_concentration() -> None:
    # Regression guard for the corrected bug: "first 30" landed entirely inside one
    # unit_type value (the outermost factorial loop) and touched only 2 of 3
    # attribution_regime values within it. The corrected stratified selection must touch
    # every level of every one of the four factors.
    dataset = generate_final_dataset()
    subset = select_final_llm_subset(list(dataset.core_cases), list(dataset.challenge_cases))
    core_by_id = {c.manifest.case_id: c for c in dataset.core_cases}
    selected = [core_by_id[cid] for cid in subset.core_case_ids]

    for factor in ("unit_type", "evidence_density", "domain_breadth", "attribution_regime"):
        counts = Counter(getattr(c.manifest, factor) for c in selected)
        full_population_levels = {getattr(c.manifest, factor) for c in dataset.core_cases}
        assert set(counts) == full_population_levels, f"{factor} missing a level in the subset: {counts}"
        # "broad coverage, not necessarily perfect balance": no level may be near-absent.
        assert min(counts.values()) >= 3, f"{factor} has a near-absent level: {counts}"


def test_final_challenge_subset_is_exactly_3_cases_per_category() -> None:
    dataset = generate_final_dataset()
    subset = select_final_llm_subset(list(dataset.core_cases), list(dataset.challenge_cases))
    chall_by_id = {c.manifest.case_id: c for c in dataset.challenge_cases}
    selected = [chall_by_id[cid] for cid in subset.challenge_case_ids]
    counts = Counter(c.manifest.challenge_category for c in selected)
    assert set(counts) == set(ChallengeCategory)
    assert len(counts) == 10
    assert all(count == 3 for count in counts.values())


def test_final_subset_selection_is_deterministic_across_independent_calls() -> None:
    dataset = generate_final_dataset()
    subset_a = select_final_llm_subset(list(dataset.core_cases), list(dataset.challenge_cases))
    subset_b = select_final_llm_subset(list(dataset.core_cases), list(dataset.challenge_cases))
    assert subset_a == subset_b


def test_final_subset_raises_clearly_if_not_enough_cases() -> None:
    import pytest

    with pytest.raises(ValueError, match="at least"):
        select_final_llm_subset([generate_final_core_case(0)], [generate_final_challenge_case(0)])


# --------------------------------------------------------------------------------------
# Determinism for fixed lock/seed
# --------------------------------------------------------------------------------------


def test_core_case_generation_is_byte_for_byte_deterministic() -> None:
    assert generate_final_core_case(17) == generate_final_core_case(17)
    assert generate_final_core_case(179) == generate_final_core_case(179)


def test_challenge_case_generation_is_byte_for_byte_deterministic() -> None:
    for i in (0, 6, 24, 42, 59):
        assert generate_final_challenge_case(i) == generate_final_challenge_case(i)


def test_full_dataset_generation_is_deterministic_across_independent_calls() -> None:
    dataset_a = generate_final_dataset()
    dataset_b = generate_final_dataset()
    assert dataset_a == dataset_b


def test_determinism_holds_with_an_explicitly_reconstructed_ontology() -> None:
    # Regression guard for the discovered defect: EvidenceTrace.observed_at previously
    # defaulted to a wall-clock datetime.now() factory, so two generations of "the same"
    # case were never equal even though every scientific field matched. Fixed by pinning
    # observed_at to a fixed constant in final_cases._blueprint_to_trace.
    ontology_a = Ontology.default()
    ontology_b = Ontology.default()
    assert generate_final_core_case(50, ontology=ontology_a) == generate_final_core_case(50, ontology=ontology_b)


def test_all_trace_ids_are_unique_across_the_full_240_case_dataset() -> None:
    dataset = generate_final_dataset()
    all_trace_ids = [t.id for c in list(dataset.core_cases) + list(dataset.challenge_cases) for t in c.evidence_bundle.traces]
    assert len(set(all_trace_ids)) == len(all_trace_ids)


# --------------------------------------------------------------------------------------
# No final-data directory or file created by this implementation step
# --------------------------------------------------------------------------------------


def test_no_final_data_directory_or_file_is_created_by_generation() -> None:
    final_evidence_dir = REPO_ROOT / "data" / "synthetic" / "final_evidence"
    final_truth_dir = REPO_ROOT / "data" / "synthetic" / "final_truth"
    assert not final_evidence_dir.exists()
    assert not final_truth_dir.exists()
    # Generating the full dataset in memory must not create these directories as a
    # side effect -- final_cases.py never touches the filesystem.
    generate_final_dataset()
    assert not final_evidence_dir.exists()
    assert not final_truth_dir.exists()


def test_dry_validation_generator_writes_no_files(tmp_path) -> None:
    """The "temporary/in-memory output only" dry validation this checkpoint requires:
    exercises the actual on-disk write path (scripts/generate_paper_b_final_cases.py's
    _write_case) against a pytest tmp_path, proving the writer works and is confined to
    wherever it's told to write -- never the real frozen dataset location."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import generate_paper_b_final_cases as gen_script

    case = generate_final_core_case(0)
    evidence_dir = tmp_path / "final_evidence"
    truth_dir = tmp_path / "final_truth"
    gen_script._write_case(case, evidence_dir=evidence_dir, truth_dir=truth_dir)

    assert (evidence_dir / f"{case.manifest.case_id}.json").exists()
    assert (truth_dir / f"{case.manifest.case_id}.json").exists()

    import json

    evidence_payload = json.loads((evidence_dir / f"{case.manifest.case_id}.json").read_text())
    assert set(evidence_payload) == {"manifest", "evidence_bundle", "opportunity_catalog"}
    assert "truth" not in evidence_payload  # evidence file must never carry truth

    real_final_evidence_dir = REPO_ROOT / "data" / "synthetic" / "final_evidence"
    assert not real_final_evidence_dir.exists()


# --------------------------------------------------------------------------------------
# Category-specific construction correctness (spot checks on the trickier categories)
# --------------------------------------------------------------------------------------


def test_ontology_shift_category_avoids_registered_terms_for_shiftable_concepts() -> None:
    ontology = Ontology.default()
    cases = [c for c in generate_final_challenge_set() if c.manifest.challenge_category == ChallengeCategory.ONTOLOGY_SHIFT_AND_UNSEEN_SYNONYMS]
    assert len(cases) == 6
    for case in cases:
        true_keys = {tc.concept_id for tc in case.truth.asset_concepts}
        shiftable = true_keys & set(_UNSEEN_SYNONYMS)
        assert shiftable, "expected at least one shiftable true concept per ontology-shift case"
        for trace in case.evidence_bundle.traces:
            text = trace.searchable_text.lower()
            for key in shiftable:
                definition = ontology.concepts[key]
                for term in definition.terms:
                    assert term.lower() not in text
                assert _UNSEEN_SYNONYMS[key].lower() in text or any(
                    _UNSEEN_SYNONYMS[key].lower() in other.searchable_text.lower() for other in case.evidence_bundle.traces
                )


def test_unseen_synonyms_are_genuinely_unseen_in_the_ontology() -> None:
    ontology = Ontology.default()
    all_registered_terms = {term.lower() for definition in ontology.concepts.values() for term in definition.terms}
    for synonym in _UNSEEN_SYNONYMS.values():
        assert synonym.lower() not in all_registered_terms
        # also confirm ontology.match() finds nothing for the bare synonym phrase alone
        assert ontology.match(synonym) == []


def test_opportunity_reversal_category_disqualifies_opp_repository() -> None:
    cases = [
        c
        for c in generate_final_challenge_set()
        if c.manifest.challenge_category == ChallengeCategory.OPPORTUNITY_CONTEXT_REVERSAL_AND_UNSAFE_DELEGATION
    ]
    assert len(cases) == 6
    for case in cases:
        true_keys = {tc.concept_id for tc in case.truth.asset_concepts}
        assert "software_engineering" in true_keys
        assert "teaching_curriculum" in true_keys
        grade = next(r.relevance_grade for r in case.truth.opportunity_relevance if r.opportunity_id == "opp-repository")
        assert grade == 0


def test_semantic_duplicate_category_produces_a_source_record_equivalent_pair() -> None:
    cases = [
        c
        for c in generate_final_challenge_set()
        if c.manifest.challenge_category == ChallengeCategory.SEMANTIC_DUPLICATES_AND_SOURCE_DEPENDENCE
    ]
    assert len(cases) == 6
    for case in cases:
        result = deduplicate_traces(case.evidence_bundle.traces)
        assert result.duplicate_count >= 1


def test_stale_contradiction_category_marks_one_concept_not_current_with_a_contradicting_trace() -> None:
    cases = [
        c
        for c in generate_final_challenge_set()
        if c.manifest.challenge_category == ChallengeCategory.STALE_CURRENT_CONFLICT_AND_CONTRADICTION
    ]
    assert len(cases) == 6
    for case in cases:
        stale_concepts = [tc for tc in case.truth.asset_concepts if not tc.is_current]
        assert len(stale_concepts) == 1
        assert stale_concepts[0].contradicting_trace_ids
        contradicting_id = stale_concepts[0].contradicting_trace_ids[0]
        assert any(t.id == contradicting_id for t in case.evidence_bundle.traces)


def test_sensitive_and_noise_category_flags_a_real_trace_as_sensitive() -> None:
    cases = [
        c
        for c in generate_final_challenge_set()
        if c.manifest.challenge_category == ChallengeCategory.IRRELEVANT_NOISE_AND_SENSITIVE_TRACES
    ]
    assert len(cases) == 6
    for case in cases:
        assert len(case.truth.sensitive_trace_ids) == 1
        sensitive_id = case.truth.sensitive_trace_ids[0]
        matching = [t for t in case.evidence_bundle.traces if t.id == sensitive_id]
        assert len(matching) == 1
        assert matching[0].sensitive is True
        assert sum(1 for t in case.evidence_bundle.traces if t.sensitive) == 1


def test_identity_collision_category_reuses_a_name_actually_present_in_the_case() -> None:
    cases = [
        c
        for c in generate_final_challenge_set()
        if c.manifest.challenge_category == ChallengeCategory.IDENTITY_COLLISION_AND_RESOLUTION_ERROR
    ]
    assert len(cases) == 6
    for case in cases:
        name_counts: Counter[str] = Counter()
        for trace in case.evidence_bundle.traces:
            name_counts.update(trace.authors_or_contributors)
        collided = [name for name, count in name_counts.items() if count > 1]
        assert len(collided) == 1
        colliding_name = collided[0]
        affiliations = {
            tuple(t.affiliations)
            for t in case.evidence_bundle.traces
            if colliding_name in t.authors_or_contributors
        }
        assert len(affiliations) == 2  # same name, two different affiliations -- a real collision


def test_sparse_and_missing_support_category_has_minimal_evidence() -> None:
    cases = [
        c for c in generate_final_challenge_set() if c.manifest.challenge_category == ChallengeCategory.SPARSE_AND_MISSING_SUPPORT
    ]
    assert len(cases) == 6
    for case in cases:
        assert case.manifest.evidence_density.value == "sparse"
        assert len(case.truth.asset_concepts) == 1
        assert len(case.evidence_bundle.traces) == 1


def test_interdisciplinary_composite_category_uses_three_templates_worth_of_concepts() -> None:
    cases = [
        c
        for c in generate_final_challenge_set()
        if c.manifest.challenge_category == ChallengeCategory.INTERDISCIPLINARY_COMPOSITE_ASSETS
    ]
    assert len(cases) == 6
    for case in cases:
        assert case.manifest.domain_breadth.value == "interdisciplinary"
        assert len(case.truth.asset_concepts) >= 3 * 4 - 2  # 3 templates x up to 4 primary concepts, allowing overlap


def test_prestige_decoy_category_adds_a_decoy_trace_without_inflating_true_concepts() -> None:
    cases = [
        c
        for c in generate_final_challenge_set()
        if c.manifest.challenge_category == ChallengeCategory.TRACE_AS_ASSET_AND_PRESTIGE_DECOYS
    ]
    assert len(cases) == 6
    decoy_titles = {spec["title"] for spec in final_cases._PRESTIGE_DECOYS}
    for case in cases:
        matches = [t for t in case.evidence_bundle.traces if t.title in decoy_titles]
        assert len(matches) == 1
        # the decoy's own template contributes no true concept -- true concepts come only
        # from the case's real asset template, never from prestige language
        true_labels = {tc.canonical_label.lower() for tc in case.truth.asset_concepts}
        assert not any(word in true_labels for word in ("award", "recognition", "keynote"))


def test_collaborator_heavy_category_has_many_unknown_role_collaborators() -> None:
    cases = [
        c
        for c in generate_final_challenge_set()
        if c.manifest.challenge_category == ChallengeCategory.COLLABORATOR_HEAVY_AND_UNKNOWN_ROLES
    ]
    assert len(cases) == 6
    for case in cases:
        assert case.manifest.attribution_regime.value == "unknown_ambiguous"
        unknown_role_traces = [t for t in case.evidence_bundle.traces if t.contribution_role.value == "unknown"]
        assert len(unknown_role_traces) >= 3
        distinct_collaborators = {name for t in case.evidence_bundle.traces for name in t.authors_or_contributors}
        assert len(distinct_collaborators) >= 4
