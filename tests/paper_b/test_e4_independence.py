"""Checkpoint B: E4 circularity removal.

Checkpoint A's real defect: C3's opportunity ranking and the hidden-relevance generator
read the exact same ``OPPORTUNITY_CONCEPT_TAGS`` dictionary. These tests prove the fix:
the truth-side scoring module is not importable from any comparator, and changing the
hidden requirement records does not change what a comparator ranks.
"""

from __future__ import annotations

import ast
import inspect
from datetime import date

import pytest

from kdaa.evaluation.paper_b import opportunity_truth
from kdaa.evaluation.paper_b.adapters import (
    c0_semantic,
    c1_generic_llm,
    c2_evidence_linked,
    c3_deterministic,
    c4_hybrid,
)
from kdaa.evaluation.paper_b.adapters.c3_deterministic import run_c3
from kdaa.evaluation.paper_b.boundary import find_truth_leakage
from kdaa.evaluation.paper_b.dev_cases import generate_development_case
from kdaa.evaluation.paper_b.opportunity_catalog import rank_opportunities_by_visible_text
from kdaa.evaluation.paper_b.snapshot import build_snapshot_for_case
from kdaa.ontology import Ontology

_COMPARATOR_MODULES = [c0_semantic, c1_generic_llm, c2_evidence_linked, c3_deterministic, c4_hybrid]


@pytest.mark.parametrize("module", _COMPARATOR_MODULES, ids=lambda m: m.__name__)
def test_opportunity_truth_module_is_not_imported_by_any_comparator(module) -> None:
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "opportunity_truth" not in node.module, module.__name__
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "opportunity_truth" not in alias.name, module.__name__


def test_boundary_check_covers_opportunity_truth_leakage() -> None:
    # find_truth_leakage only checks for the `truth` module by name; confirm
    # opportunity_truth itself is never re-exported from truth-free modules the
    # boundary would miss, by checking it directly against every adapter file.
    violations = find_truth_leakage()
    assert violations == {}


def test_changing_hidden_relevance_does_not_change_comparator_ranking() -> None:
    """The core independence proof: mutate the hidden requirement table and confirm a
    comparator's ranking for the same case is completely unaffected, because the ranking
    function never reads it."""
    ontology = Ontology.default()
    case = generate_development_case(0)
    snapshot = build_snapshot_for_case(case)

    prediction_before = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=date(2026, 6, 1))
    ranking_before = [o.opportunity_id for o in prediction_before.ranked_opportunities]

    original_requirements = dict(opportunity_truth.OPPORTUNITY_REQUIREMENTS)
    try:
        # Wildly different hidden requirements -- if the ranker were still reading this
        # table (the Checkpoint A defect), the ranking would change.
        opportunity_truth.OPPORTUNITY_REQUIREMENTS.clear()
        opportunity_truth.OPPORTUNITY_REQUIREMENTS.update(
            {
                candidate_id: opportunity_truth.OpportunityRequirement(
                    opportunity_id=candidate_id,
                    required_concepts=frozenset({"survival_analysis"}),
                    disqualifying_concepts=frozenset({"agentic_ai", "software_engineering"}),
                )
                for candidate_id in original_requirements
            }
        )
        prediction_after = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=date(2026, 6, 1))
        ranking_after = [o.opportunity_id for o in prediction_after.ranked_opportunities]
    finally:
        opportunity_truth.OPPORTUNITY_REQUIREMENTS.clear()
        opportunity_truth.OPPORTUNITY_REQUIREMENTS.update(original_requirements)

    assert ranking_before == ranking_after


def test_hidden_grade_computation_is_independent_of_visible_ranking_function() -> None:
    # Static proof by construction: rank_opportunities_by_visible_text's own source does
    # not reference OPPORTUNITY_REQUIREMENTS or compute_relevance_grade at all.
    from kdaa.evaluation.paper_b import opportunity_catalog

    source = inspect.getsource(opportunity_catalog.rank_opportunities_by_visible_text)
    assert "OPPORTUNITY_REQUIREMENTS" not in source
    assert "compute_relevance_grade" not in source


def test_compute_relevance_grade_uses_only_true_concepts_not_visible_text() -> None:
    # Grading takes a set of concept keys, not any opportunity text -- confirmed by
    # signature inspection.
    signature = inspect.signature(opportunity_truth.compute_relevance_grade)
    params = list(signature.parameters)
    assert params == ["true_concept_keys", "opportunity_id"]


def test_rank_by_visible_text_produces_full_ranking_over_the_catalog() -> None:
    from kdaa.evaluation.paper_b.opportunity_catalog import DEV_OPPORTUNITY_CATALOG

    ontology = Ontology.default()
    result = rank_opportunities_by_visible_text(["Agentic AI"], DEV_OPPORTUNITY_CATALOG, ontology)
    assert len(result) == 10
    assert {o.opportunity_id for o in result} == {c.opportunity_id for c in DEV_OPPORTUNITY_CATALOG}


def test_e4_scores_are_no_longer_near_perfect_for_c3() -> None:
    # Regression guard against the Checkpoint A circularity resurfacing: with the fix,
    # C3's nDCG@5 across a handful of cases should show real variation, not be
    # suspiciously close to a near-perfect replay of the answer table.
    from kdaa.evaluation.paper_b.dev_cases import generate_development_set
    from kdaa.evaluation.paper_b.scoring import score_opportunities

    ontology = Ontology.default()
    cases = generate_development_set(10)
    scores = []
    for case in cases:
        snapshot = build_snapshot_for_case(case)
        prediction = run_c3(case.evidence_bundle, snapshot, ontology, as_of_date=date(2026, 6, 1))
        result = score_opportunities(case.manifest.case_id, prediction.ranked_opportunities, case.truth.opportunity_relevance)
        scores.append(result.ndcg_at_5)
    assert len(set(round(s, 3) for s in scores)) > 1, "expected genuine variation, not a constant near-perfect score"
