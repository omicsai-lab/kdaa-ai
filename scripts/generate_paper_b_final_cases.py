"""Human-run CLI to materialize the frozen final Paper B N=240 dataset to disk.

Nothing in ``kdaa.evaluation.paper_b.final_cases`` calls this script, and this script is
not invoked by any other part of this implementation step -- generating the actual frozen
dataset is a deliberate, separate action for a human to take after this checkpoint's code
is reviewed, per ``configs/paper_b/final_experiment_lock.yaml``:
``case_generation_must_occur: only_after_this_freeze_is_reviewed_committed_and_pushed``.

Writes evidence (inference-visible: manifest + evidence bundle + case-specific opportunity
catalog) and truth (hidden) to two physically separate output roots. Use ``--dry-run`` to
generate and validate everything in memory without writing any file at all.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from kdaa.evaluation.paper_b.boundary import find_truth_leakage  # noqa: E402
from kdaa.evaluation.paper_b.final_cases import (  # noqa: E402
    CHALLENGE_N,
    CORE_N,
    FinalCase,
    generate_final_dataset,
)
from kdaa.evaluation.paper_b.final_llm_subset import select_final_llm_subset  # noqa: E402


def _write_case(case: FinalCase, *, evidence_dir: Path, truth_dir: Path) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    case_id = case.manifest.case_id
    evidence_payload = {
        "manifest": case.manifest.model_dump(mode="json"),
        "evidence_bundle": case.evidence_bundle.model_dump(mode="json"),
        "opportunity_catalog": [o.model_dump(mode="json") for o in case.opportunity_catalog],
    }
    (evidence_dir / f"{case_id}.json").write_text(json.dumps(evidence_payload, indent=2, sort_keys=True), encoding="utf-8")
    (truth_dir / f"{case_id}.json").write_text(
        json.dumps(case.truth.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default=str(REPO_ROOT / "data" / "synthetic"))
    parser.add_argument("--dry-run", action="store_true", help="Generate and validate only; write no files.")
    args = parser.parse_args()

    print("Generating final Paper B dataset (core + challenge)...")
    dataset = generate_final_dataset()
    print(f"  core cases: {len(dataset.core_cases)} (expected {CORE_N})")
    print(f"  challenge cases: {len(dataset.challenge_cases)} (expected {CHALLENGE_N})")
    assert len(dataset.core_cases) == CORE_N
    assert len(dataset.challenge_cases) == CHALLENGE_N
    assert dataset.total_n == 240

    subset = select_final_llm_subset(list(dataset.core_cases), list(dataset.challenge_cases))
    print(
        f"  final LLM subset: {subset.n_core} core + {subset.n_challenge} challenge = {subset.n}; "
        f"intended live calls = {subset.intended_primary_live_llm_calls}"
    )
    assert subset.intended_primary_live_llm_calls == 540

    violations = find_truth_leakage()
    if violations:
        print(f"TRUTH LEAKAGE DETECTED, aborting: {violations}")
        return 1
    print("  truth/inference boundary check: OK")

    if args.dry_run:
        print("\n--dry-run: no files written.")
        return 0

    evidence_dir = Path(args.output_root) / "final_evidence"
    truth_dir = Path(args.output_root) / "final_truth"
    for case in list(dataset.core_cases) + list(dataset.challenge_cases):
        _write_case(case, evidence_dir=evidence_dir, truth_dir=truth_dir)
    print(f"\nWrote {dataset.total_n} cases to:\n  {evidence_dir}\n  {truth_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
