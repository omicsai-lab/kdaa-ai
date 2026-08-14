"""Controlled engineering benchmarks for the MVP."""

from .benchmark import BenchmarkResult, run_synthetic_benchmark
from .robustness import RobustnessResult, run_robustness_suite

__all__ = [
    "BenchmarkResult",
    "RobustnessResult",
    "run_robustness_suite",
    "run_synthetic_benchmark",
]
