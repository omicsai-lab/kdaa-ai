"""Final Paper B execution runner.

**This implementation step never runs this script against real final data.** It exists so
the final execution layer (``kdaa.evaluation.paper_b.final_run``) can be dry-validated now
(fake provider, in-memory or temporary-directory generated cases) and reused unchanged
later, when a human decides to execute the real frozen final study.

``--dry-run`` (default): generates a fresh, in-memory 240-case dataset via
``final_cases.generate_final_dataset`` (NOT the committed ``data/synthetic/final_*``
paths -- nothing under this implementation step writes there), selects the frozen 60-case
LLM subset, and runs every block (deterministic, LLM, ablations, robustness) with a fake
provider. Optionally writes outputs to ``--output-root`` (default: a mkdtemp temporary
directory, never the real ``results/paper_b/final/``).
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import asdict
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from kdaa.evaluation.paper_b.adapters.fake_provider import always_succeeding_provider  # noqa: E402
from kdaa.evaluation.paper_b.final_cases import generate_final_dataset  # noqa: E402
from kdaa.evaluation.paper_b.final_llm_subset import select_final_llm_subset  # noqa: E402
from kdaa.evaluation.paper_b.final_run import (  # noqa: E402
    FINAL_OUTPUT_SUBDIRS,
    build_final_paired_comparisons,
    ensure_final_output_layout,
    run_final_ablations,
    run_final_deterministic_block,
    run_final_llm_block,
    run_final_robustness,
)
from kdaa.ontology import Ontology  # noqa: E402

_FAKE_OPPORTUNITY_IDS = [
    "opp-repository",
    "opp-living-document",
    "opp-knowledge-base",
    "opp-deployable-product",
    "opp-public-content",
    "opp-grant-proposal",
    "opp-benchmark-dataset",
    "opp-training-course",
    "opp-consulting-service",
    "opp-methods-paper",
]


def _to_jsonable(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "__dataclass_fields__"):
        return {k: _to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value


def _write_outputs(output_root: Path, *, deterministic, llm, ablations, robustness, comparisons) -> None:
    ensure_final_output_layout(output_root)
    (output_root / "metrics" / "deterministic_case_scores.json").write_text(
        json.dumps(_to_jsonable(list(deterministic.case_scores)), indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_root / "raw" / "llm_attempts.json").write_text(
        json.dumps(_to_jsonable(list(llm.all_attempts)), indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_root / "metrics" / "llm_repeated_scores.json").write_text(
        json.dumps(_to_jsonable(list(llm.repeated_scores)), indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_root / "ablations" / "ablation_results.json").write_text(
        json.dumps(_to_jsonable(ablations), indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_root / "robustness" / "robustness_results.json").write_text(
        json.dumps(_to_jsonable(robustness), indent=2, sort_keys=True), encoding="utf-8"
    )
    (output_root / "summary" / "paired_comparisons.json").write_text(
        json.dumps(_to_jsonable(comparisons), indent=2, sort_keys=True), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", default=True, help="Fake provider, no live calls (default).")
    parser.add_argument("--as-of-date", default="2026-06-01")
    parser.add_argument("--output-root", default=None, help="Default: a temporary directory (never real final results).")
    parser.add_argument("--write-outputs", action="store_true", help="Write outputs to --output-root.")
    args = parser.parse_args()

    as_of_date = date.fromisoformat(args.as_of_date)
    ontology = Ontology.default()

    print("Generating an in-memory 240-case final dataset (not data/synthetic/final_*)...")
    dataset = generate_final_dataset(ontology=ontology)
    all_cases = list(dataset.core_cases) + list(dataset.challenge_cases)
    print(f"  core={len(dataset.core_cases)} challenge={len(dataset.challenge_cases)} total={len(all_cases)}")

    subset = select_final_llm_subset(list(dataset.core_cases), list(dataset.challenge_cases))
    subset_ids = set(subset.core_case_ids) | set(subset.challenge_case_ids)
    subset_cases = [c for c in all_cases if c.manifest.case_id in subset_ids]
    print(f"  LLM/ablation/robustness subset (PC-09, shared): {len(subset_cases)} cases")

    print("\nRunning final deterministic block (C0-S, C3) on all cases...")
    deterministic = run_final_deterministic_block(all_cases, as_of_date=as_of_date, ontology=ontology)
    print(f"  case_scores: {len(deterministic.case_scores)} (expected {2 * len(all_cases)})")

    provider = always_succeeding_provider(
        concepts=[{"label": "Agentic AI", "ownership": "focal_unit"}],
        ranked_opportunity_ids=_FAKE_OPPORTUNITY_IDS,
    )
    print("\nRunning final LLM block (C1, C2, C4) on the frozen 60-case subset [FAKE PROVIDER]...")
    llm = run_final_llm_block(
        subset_cases, provider_c1=provider, provider_c2=provider, provider_c4=provider, ontology=ontology, as_of_date=as_of_date
    )
    print(f"  intended calls: {llm.intended_calls} (expected 540 at real N=60)")
    print(f"  attempts recorded: {len(llm.all_attempts)}")

    print("\nRunning final ablations (A1/A4/A6) on the same subset...")
    ablations = run_final_ablations(subset_cases, ontology, as_of_date=as_of_date)
    print(f"  ablation results: {len(ablations)} (expected {3 * len(subset_cases)})")

    print("\nRunning final robustness (R1/R2/R3 -- 4 perturbation variants) on the same subset...")
    robustness = run_final_robustness(subset_cases, ontology, as_of_date=as_of_date)
    print(f"  robustness results: {len(robustness)} (expected {4 * len(subset_cases)})")

    print("\nBuilding final paired comparisons (no live/composite score)...")
    comparisons = build_final_paired_comparisons(
        deterministic, llm, llm_subset_case_ids=tuple(subset.core_case_ids + subset.challenge_case_ids)
    )
    print(f"  contrasts: {sorted(comparisons)}")

    output_root = Path(args.output_root) if args.output_root else Path(tempfile.mkdtemp(prefix="paper_b_final_dry_"))
    if args.write_outputs:
        _write_outputs(output_root, deterministic=deterministic, llm=llm, ablations=ablations, robustness=robustness, comparisons=comparisons)
        print(f"\nWrote dry-validation outputs to: {output_root}")
        print(f"  subdirectories: {FINAL_OUTPUT_SUBDIRS}")
    else:
        ensure_final_output_layout(output_root)
        print(f"\nCreated empty output-layout skeleton only (no results written) at: {output_root}")

    real_final_dir = REPO_ROOT / "data" / "synthetic"
    print(f"\nreal final dataset directory exists: {(real_final_dir / 'final_evidence').exists()} (must be False)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
