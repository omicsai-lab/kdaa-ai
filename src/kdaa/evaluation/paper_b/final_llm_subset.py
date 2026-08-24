"""Frozen final LLM subset selection (30 core + 30 challenge = 60), per
``configs/paper_b/final_experiment_lock.yaml`` ``final_llm_subset``.

**Correction** (this checkpoint): the first implementation took "the first 30" cases of
each set by raw generation order. That was a real bug, not just a simplification: the core
factorial cells are generated in nested-loop order with ``unit_type`` outermost (12 cells
per unit_type, 5 replicates each = 60 flat indices per unit_type), so "the first 30" landed
entirely inside the first unit_type value and never touched the other two -- a systematic
concentration bug, not sampling noise. The challenge set has the same problem: "the first
30" of 60 challenge cases (6 per category, 10 categories) covers only the first 5
categories and skips the other 5 entirely.

This version replaces raw generation-order slicing with deterministic **systematic
sampling** (evenly-spaced index selection -- a standard, simple stratification method),
applied per stratum:

- **Core**: cases are grouped by their factorial cell (``unit_type``, ``evidence_density``,
  ``domain_breadth``, ``attribution_regime``) using only ``CaseManifest.seed`` (which
  ``final_cases.py`` sets to each case's flat generation index, so
  ``cell_index = seed // replicates_per_cell``); 30 of the 36 cells are selected by
  systematic sampling over cell index, and one replicate per selected cell is chosen by
  cycling the replicate slot across selections (so the same replicate slot -- e.g. always
  "replicate 0" -- is not always picked). Selection reads only manifest fields, which
  ``dev_cases.py``'s own docstring already establishes are inference-safe/design metadata,
  never truth.
- **Challenge**: exactly 3 of each category's 6 cases, again by systematic sampling of the
  replicate index within each category, iterated in the frozen ``ChallengeCategory``
  declaration order (matching ``experiment_lock.yaml``'s ``challenge_categories`` list).

Both selections depend only on ``CaseManifest`` fields (never ``TruthBundle``, a
comparator's prediction, or an observed score), verified structurally by an AST purity
check (mirroring ``tests/paper_b/test_dev_llm_subset.py``'s development-stage guard) and
empirically by a test that mutates every case's hidden truth and confirms the selection is
unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass

from .final_cases import FinalCase
from .schemas import ChallengeCategory

DEFAULT_FINAL_LLM_SUBSET_CORE_N = 30
DEFAULT_FINAL_LLM_SUBSET_CHALLENGE_N_PER_CATEGORY = 3


@dataclass(frozen=True)
class FrozenFinalLLMSubset:
    core_case_ids: tuple[str, ...]
    challenge_case_ids: tuple[str, ...]
    n: int
    n_core: int
    n_challenge: int
    intended_repeats_per_case: int
    comparators: tuple[str, ...]

    @property
    def intended_primary_live_llm_calls(self) -> int:
        return self.n * self.intended_repeats_per_case * len(self.comparators)


def _systematic_indices(n_items: int, n_select: int) -> list[int]:
    """Standard systematic (evenly-spaced) sampling: ``n_select`` strictly increasing,
    deterministic indices into a length-``n_items`` sequence. Requires ``n_select <=
    n_items``; spacing is ``n_items / n_select`` on average, so results are spread across
    the full range rather than concentrated at one end."""
    if n_select > n_items:
        raise ValueError(f"cannot select {n_select} items from only {n_items}")
    return [(i * n_items) // n_select for i in range(n_select)]


def _select_stratified_core_ids(core_cases: list[FinalCase], *, n_core: int) -> tuple[str, ...]:
    # Group by factorial cell (unit_type, evidence_density, domain_breadth,
    # attribution_regime) -- reads only inference-safe CaseManifest fields, never truth.
    cell_of: dict[tuple, list[FinalCase]] = {}
    for case in core_cases:
        if case.manifest.seed is None:
            raise ValueError(f"core case {case.manifest.case_id} has no seed; cannot stratify")
        key = (case.manifest.unit_type, case.manifest.evidence_density, case.manifest.domain_breadth, case.manifest.attribution_regime)
        cell_of.setdefault(key, []).append(case)
    for cases in cell_of.values():
        cases.sort(key=lambda c: c.manifest.seed)

    # Deterministic cell order: each cell's own lowest seed (its generation-order position).
    cell_keys = sorted(cell_of, key=lambda k: min(c.manifest.seed for c in cell_of[k]))
    total_cells = len(cell_keys)
    if n_core > total_cells:
        # More cases requested than cells exist: fall back to systematic sampling over the
        # full flat case list instead (still never uses output/truth).
        flat = sorted(core_cases, key=lambda c: c.manifest.seed)
        return tuple(flat[i].manifest.case_id for i in _systematic_indices(len(flat), n_core))

    selected_cell_positions = _systematic_indices(total_cells, n_core)
    selected_ids: list[str] = []
    for pick_index, cell_position in enumerate(selected_cell_positions):
        cell_cases = cell_of[cell_keys[cell_position]]
        replicate_slot = pick_index % len(cell_cases)
        selected_ids.append(cell_cases[replicate_slot].manifest.case_id)
    return tuple(selected_ids)


def _select_stratified_challenge_ids(challenge_cases: list[FinalCase], *, n_per_category: int) -> tuple[str, ...]:
    by_category: dict[ChallengeCategory, list[FinalCase]] = {}
    for case in challenge_cases:
        category = case.manifest.challenge_category
        if category is None:
            raise ValueError(f"challenge case {case.manifest.case_id} has no challenge_category")
        by_category.setdefault(category, []).append(case)
    for cases in by_category.values():
        cases.sort(key=lambda c: c.manifest.seed)

    selected_ids: list[str] = []
    for category in ChallengeCategory:  # frozen declaration order
        cases = by_category.get(category, [])
        for position in _systematic_indices(len(cases), n_per_category):
            selected_ids.append(cases[position].manifest.case_id)
    return tuple(selected_ids)


def select_final_llm_subset(
    core_cases: list[FinalCase],
    challenge_cases: list[FinalCase],
    *,
    n_core: int = DEFAULT_FINAL_LLM_SUBSET_CORE_N,
    n_per_challenge_category: int = DEFAULT_FINAL_LLM_SUBSET_CHALLENGE_N_PER_CATEGORY,
    intended_repeats_per_case: int = 3,
    comparators: tuple[str, ...] = ("C1", "C2", "C4"),
) -> FrozenFinalLLMSubset:
    """Select and freeze the final LLM comparison subset: ``n_core`` core cases via
    stratified systematic sampling across all four factorial dimensions, and exactly
    ``n_per_challenge_category`` cases from each of the 10 challenge categories. Must be
    called, and its result recorded, before any live model result is observed -- selection
    depends only on ``CaseManifest`` fields (generation-order seed and challenge category),
    never on anything derived from a comparator's output or hidden truth."""
    if len(core_cases) < n_core:
        raise ValueError(f"Need at least {n_core} core cases to select a subset of {n_core}; got {len(core_cases)}")
    n_categories = len(ChallengeCategory)
    n_challenge = n_per_challenge_category * n_categories
    if len(challenge_cases) < n_challenge:
        raise ValueError(
            f"Need at least {n_challenge} challenge cases ({n_per_challenge_category} x {n_categories} categories); "
            f"got {len(challenge_cases)}"
        )

    core_ids = _select_stratified_core_ids(core_cases, n_core=n_core)
    challenge_ids = _select_stratified_challenge_ids(challenge_cases, n_per_category=n_per_challenge_category)

    return FrozenFinalLLMSubset(
        core_case_ids=core_ids,
        challenge_case_ids=challenge_ids,
        n=len(core_ids) + len(challenge_ids),
        n_core=len(core_ids),
        n_challenge=len(challenge_ids),
        intended_repeats_per_case=intended_repeats_per_case,
        comparators=comparators,
    )
