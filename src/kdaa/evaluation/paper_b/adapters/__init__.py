"""Comparator adapters for Paper B (Checkpoint B: C0-S, C1, C2, C3, C4).

Every module in this package is under the truth-import boundary enforced by
``kdaa.evaluation.paper_b.boundary.find_truth_leakage`` -- none may import
``kdaa.evaluation.paper_b.truth`` or ``kdaa.evaluation.paper_b.opportunity_truth``,
directly or via this package's own re-exports (this ``__init__`` deliberately does not
import ``dev_cases`` or anything else that touches truth).
"""

from __future__ import annotations

from .c0_semantic import run_c0_s
from .c1_generic_llm import run_c1
from .c2_evidence_linked import run_c2
from .c3_deterministic import run_c3
from .c4_hybrid import run_c4

__all__ = ["run_c0_s", "run_c1", "run_c2", "run_c3", "run_c4"]
