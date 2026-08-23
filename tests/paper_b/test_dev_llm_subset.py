from collections import Counter

import pytest

from kdaa.evaluation.paper_b.dev_cases import generate_development_set
from kdaa.evaluation.paper_b.dev_llm_subset import (
    DEFAULT_LLM_SUBSET_SIZE,
    select_development_llm_subset,
)


def test_default_subset_size_is_in_the_required_range() -> None:
    assert 24 <= DEFAULT_LLM_SUBSET_SIZE <= 30


def test_subset_is_frozen_deterministically_by_generation_order() -> None:
    cases = generate_development_set(60)
    subset_a = select_development_llm_subset(cases)
    subset_b = select_development_llm_subset(cases)
    assert subset_a.case_ids == subset_b.case_ids
    assert subset_a.case_ids == tuple(case.manifest.case_id for case in cases[: subset_a.n])


def test_subset_selection_does_not_depend_on_any_prediction_or_truth_value() -> None:
    # Structural guard: selection reads only case.manifest.case_id (generation order),
    # never anything from case.truth or a comparator's output.
    import ast
    import inspect

    from kdaa.evaluation.paper_b import dev_llm_subset

    source = inspect.getsource(dev_llm_subset.select_development_llm_subset)
    tree = ast.parse(source)
    attributes_accessed = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "truth" not in attributes_accessed


def test_subset_raises_clearly_if_not_enough_cases() -> None:
    cases = generate_development_set(10)
    with pytest.raises(ValueError, match="at least"):
        select_development_llm_subset(cases, n=30)


def test_subset_is_balanced_across_the_four_required_dimensions() -> None:
    cases = generate_development_set(60)
    subset = select_development_llm_subset(cases, n=30)
    selected = [case for case in cases if case.manifest.case_id in set(subset.case_ids)]

    unit_types = Counter(case.manifest.unit_type.value for case in selected)
    densities = Counter(case.manifest.evidence_density.value for case in selected)
    domains = Counter(case.manifest.domain_breadth.value for case in selected)
    ownerships = Counter(
        case.truth.asset_concepts[0].ownership_state.value for case in selected if case.truth.asset_concepts
    )

    assert set(unit_types) == {"individual_researcher", "team", "laboratory"}
    assert set(densities) == {"sparse", "dense"}
    assert set(domains) == {"single_domain", "interdisciplinary"}
    assert set(ownerships) == {"focal_unit", "shared", "organizational", "external", "unresolved"}
    # Exact balance for the three uniformly-cycled dimensions (unit_type: 1/3 each,
    # evidence_density: 1/2 each, ownership: 1/5 each) -- the subset size (30) is the LCM
    # of their cycle periods (3, 2, 5). domain_breadth is a period-3 cycle but not a 3-way
    # split (1-in-3 interdisciplinary, 2-in-3 single_domain -- see dev_cases.py), so it is
    # proportionally, not equally, balanced: 10 vs 20 of 30.
    assert len(set(unit_types.values())) == 1
    assert len(set(densities.values())) == 1
    assert len(set(ownerships.values())) == 1
    assert domains["interdisciplinary"] == 10
    assert domains["single_domain"] == 20
