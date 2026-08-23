"""Frozen development LLM subset selection (Checkpoint B Section 7).

``generate_development_set`` cycles its four design dimensions deterministically by case
index: unit_type (period 3), evidence_density (period 2), domain_breadth (period 3),
ownership regime (period 5). ``lcm(3, 2, 3, 5) = 30``, so the first 30 cases (indices
0-29) already contain exactly one full period of every dimension -- a perfectly balanced
subset with no sampling logic needed. This module exists solely to name that subset
explicitly, once, so it can be frozen (recorded and never re-derived from live results).
"""

from __future__ import annotations

from dataclasses import dataclass

from .dev_cases import DevelopmentCase

DEFAULT_LLM_SUBSET_SIZE = 30


@dataclass(frozen=True)
class FrozenLLMSubset:
    case_ids: tuple[str, ...]
    n: int


def select_development_llm_subset(
    cases: list[DevelopmentCase], *, n: int = DEFAULT_LLM_SUBSET_SIZE
) -> FrozenLLMSubset:
    """Select and freeze the first ``n`` development cases (by generation index) as the
    LLM comparison subset. Must be called, and its result recorded, before any live model
    result is observed -- selection depends only on case generation order, never on
    anything derived from a comparator's output.
    """
    if len(cases) < n:
        raise ValueError(f"Need at least {n} development cases to select a subset of {n}; got {len(cases)}")
    selected = cases[:n]
    return FrozenLLMSubset(case_ids=tuple(case.manifest.case_id for case in selected), n=n)
