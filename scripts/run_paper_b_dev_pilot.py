#!/usr/bin/env python
"""Paper B Checkpoint A development pilot: C3 vs C0-S on E1-E4, development cases only.

DEVELOPMENT ONLY -- NOT FINAL PAPER RESULTS. Writes to results/paper_b/development/,
never to any committed v0.1 or final Paper B result path.

Usage:
    python scripts/run_paper_b_dev_pilot.py [--n-cases 60] [--as-of-date 2026-06-01]
        [--seed 42] [--output results/paper_b/development]
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from kdaa.evaluation.paper_b.dev_pilot import (
    DEVELOPMENT_LABEL,
    run_development_pilot,
    write_development_outputs,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-cases", type=int, default=60)
    parser.add_argument("--as-of-date", type=str, default="2026-06-01")
    parser.add_argument("--seed", type=int, default=42, help="Bootstrap CI seed")
    parser.add_argument("--output", type=str, default="results/paper_b/development")
    args = parser.parse_args()

    as_of_date = date.fromisoformat(args.as_of_date)
    result = run_development_pilot(n_cases=args.n_cases, as_of_date=as_of_date, bootstrap_seed=args.seed)
    write_development_outputs(result, args.output)

    print(f"\n{DEVELOPMENT_LABEL}\n")
    print(f"Cases: {result.n_cases}  as_of_date: {result.as_of_date}  runtime: {result.runtime_seconds:.2f}s")
    print(f"Outputs: {Path(args.output).resolve()}\n")
    print(f"{'metric':<28}{'C3 mean':>10}{'C0-S mean':>10}{'C3-C0S':>10}{'median':>10}{'95% CI':>18}")
    for name, summary in result.paired_summaries.items():
        ci = f"[{summary.ci95_low:.3f}, {summary.ci95_high:.3f}]"
        print(
            f"{name:<28}{summary.mean_a:>10.3f}{summary.mean_b:>10.3f}"
            f"{summary.mean_paired_difference:>10.3f}{summary.median_paired_difference:>10.3f}{ci:>18}"
            f"  (n={summary.n_cases})"
        )


if __name__ == "__main__":
    main()
