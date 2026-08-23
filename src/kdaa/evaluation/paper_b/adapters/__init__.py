"""Comparator adapters for Paper B (Checkpoint A: C0-S and C3 only).

Every module in this package is under the truth-import boundary enforced by
``kdaa.evaluation.paper_b.boundary.find_truth_leakage`` -- none may import
``kdaa.evaluation.paper_b.truth``, directly or via this package's own re-exports (this
``__init__`` deliberately does not import ``dev_cases`` or anything else that touches
truth).
"""

from __future__ import annotations

from .c0_semantic import run_c0_s
from .c3_deterministic import run_c3

__all__ = ["run_c0_s", "run_c3"]
