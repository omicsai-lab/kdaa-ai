"""Development-stage paired comparison summary (Checkpoint A).

Deliberately not the final inferential-statistics framework (no p-values, no multiple-
comparison adjustment): case-level paired distributions, mean/median differences, and a
simple percentile paired bootstrap CI are sufficient to debug and interpret Checkpoint A.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

DEFAULT_BOOTSTRAP_RESAMPLES = 2000


@dataclass(frozen=True)
class PairedMetricSummary:
    metric_name: str
    n_cases: int
    mean_a: float
    mean_b: float
    mean_paired_difference: float  # a - b
    median_paired_difference: float
    ci95_low: float
    ci95_high: float
    per_case_differences: tuple[float, ...]


def paired_bootstrap_ci(
    differences: list[float], *, n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES, seed: int = 42
) -> tuple[float, float]:
    """Simple percentile paired bootstrap CI over case-level differences.

    Resamples cases (with replacement) as a block -- each resample recomputes the mean
    difference for that resampled set of cases, preserving the pairing. Deterministic
    given a fixed ``seed``.
    """
    n = len(differences)
    if n == 0:
        return (0.0, 0.0)
    if n == 1:
        return (differences[0], differences[0])
    rng = random.Random(seed)
    resampled_means = []
    for _ in range(n_resamples):
        sample = [differences[rng.randrange(n)] for _ in range(n)]
        resampled_means.append(statistics.mean(sample))
    resampled_means.sort()
    low_index = max(0, int(0.025 * n_resamples))
    high_index = min(n_resamples - 1, int(0.975 * n_resamples))
    return (resampled_means[low_index], resampled_means[high_index])


def summarize_paired(
    metric_name: str,
    values_a: list[float],
    values_b: list[float],
    *,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = 42,
) -> PairedMetricSummary:
    """Summarize a paired (same case, two comparators) metric. ``values_a``/``values_b``
    must already be filtered to only the cases where both are applicable (e.g. E3's
    excluded-denominator cases dropped from both lists before calling this)."""
    if len(values_a) != len(values_b):
        raise ValueError("values_a and values_b must have the same length (paired by case)")
    n = len(values_a)
    differences = [a - b for a, b in zip(values_a, values_b, strict=True)]
    if n == 0:
        return PairedMetricSummary(
            metric_name=metric_name,
            n_cases=0,
            mean_a=0.0,
            mean_b=0.0,
            mean_paired_difference=0.0,
            median_paired_difference=0.0,
            ci95_low=0.0,
            ci95_high=0.0,
            per_case_differences=(),
        )
    ci_low, ci_high = paired_bootstrap_ci(differences, n_resamples=n_resamples, seed=seed)
    return PairedMetricSummary(
        metric_name=metric_name,
        n_cases=n,
        mean_a=statistics.mean(values_a),
        mean_b=statistics.mean(values_b),
        mean_paired_difference=statistics.mean(differences),
        median_paired_difference=statistics.median(differences),
        ci95_low=ci_low,
        ci95_high=ci_high,
        per_case_differences=tuple(differences),
    )
