#!/usr/bin/env python
"""Paper B Checkpoint B development pilot: C1/C2/C4 vs C3/C0-S, ablations, robustness.

DEVELOPMENT ONLY -- NOT FINAL PAPER RESULTS. Writes to
results/paper_b/development/checkpoint_b/, never to Checkpoint A's or any committed
final-result path.

Usage:
    python scripts/run_paper_b_dev_llm.py --dry-run
        Fake-provider validation only. No credentials required, no live calls made.

    python scripts/run_paper_b_dev_llm.py
        Live run. Requires KDAA_LLM_API_KEY (and KDAA_LLM_MODEL; KDAA_LLM_BASE_URL
        optional, defaults to the OpenAI-compatible default) in the environment. C1, C2,
        and C4 use one shared provider instance -- the same model configuration for all
        three (Checkpoint B Section 5). Exits with an explanatory message instead of
        running live if no valid configuration is found.
"""

from __future__ import annotations

import argparse
import os
from datetime import date

from kdaa.evaluation.paper_b.adapters.fake_provider import FakeJSONProvider
from kdaa.evaluation.paper_b.dev_cases import generate_development_set
from kdaa.evaluation.paper_b.dev_llm_subset import select_development_llm_subset
from kdaa.evaluation.paper_b.dev_pilot_llm import (
    DEVELOPMENT_LABEL,
    run_ablations,
    run_llm_development_pilot,
    run_robustness,
    write_checkpoint_b_outputs,
)
from kdaa.evaluation.paper_b.leakage import validate_case_leakage
from kdaa.evaluation.paper_b.opportunity_catalog import DEV_OPPORTUNITY_CATALOG
from kdaa.evaluation.paper_b.snapshot import build_snapshot_for_case
from kdaa.ontology import Ontology
from kdaa.providers.base import JSONProvider


def _fake_provider() -> FakeJSONProvider:
    """Deterministic, always-succeeding fake response for --dry-run validation only.
    Proves the harness runs end-to-end; the resulting scores are not meaningful and must
    not be reported as evidence of any comparator's real capability.
    """
    fake_response = {
        "concepts": [{"label": "Generic capability", "ownership": "unresolved"}],
        "ranked_opportunity_ids": [candidate.opportunity_id for candidate in DEV_OPPORTUNITY_CATALOG],
    }
    return FakeJSONProvider([fake_response], model_name="fake-dev-model-checkpoint-b")


def _resolve_live_provider() -> JSONProvider:
    from kdaa.providers.openai_compatible import OpenAICompatibleProvider

    api_key = os.getenv("KDAA_LLM_API_KEY")
    model = os.getenv("KDAA_LLM_MODEL")
    base_url = os.getenv("KDAA_LLM_BASE_URL", "https://api.openai.com/v1")
    if not api_key or not model:
        raise SystemExit(
            "No live model configuration found.\n"
            "Set KDAA_LLM_API_KEY and KDAA_LLM_MODEL (optionally KDAA_LLM_BASE_URL) in the "
            "environment to run live, or pass --dry-run to validate the pipeline with a "
            "fake provider and no credentials.\n"
            "This script deliberately does not search Desktop/Documents/Downloads or any "
            "other filesystem location for credentials."
        )
    return OpenAICompatibleProvider(base_url=base_url, api_key=api_key, model=model)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Use a fake provider; no live calls.")
    parser.add_argument("--n-cases", type=int, default=60)
    parser.add_argument("--llm-subset-size", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--as-of-date", type=str, default="2026-06-01")
    parser.add_argument("--ablation-robustness-n", type=int, default=12)
    parser.add_argument("--output", type=str, default="results/paper_b/development/checkpoint_b")
    args = parser.parse_args()

    as_of_date = date.fromisoformat(args.as_of_date)
    ontology = Ontology.default()

    cases = generate_development_set(args.n_cases, ontology=ontology)
    subset = select_development_llm_subset(cases, n=args.llm_subset_size)
    subset_case_ids = set(subset.case_ids)
    subset_cases = [case for case in cases if case.manifest.case_id in subset_case_ids]

    print(f"{DEVELOPMENT_LABEL}\n")
    print(f"Frozen LLM development subset: N={subset.n} (indices 0-{subset.n - 1} of {args.n_cases})")

    for case in subset_cases:
        snapshot = build_snapshot_for_case(case)
        validate_case_leakage(case.evidence_bundle, case.truth, snapshot)
    print("Leakage validation: passed for all subset cases.")

    provider = _fake_provider() if args.dry_run else _resolve_live_provider()
    print(f"Provider: {'FAKE (dry-run)' if args.dry_run else 'LIVE'}  model={provider.model_name}")

    llm_result = run_llm_development_pilot(
        subset_cases,
        provider_c1=provider,
        provider_c2=provider,
        provider_c4=provider,
        ontology=ontology,
        as_of_date=as_of_date,
        n_repeats=args.repeats,
    )
    print(
        f"LLM comparisons: {llm_result.n_cases} cases x {llm_result.n_repeats} repeats x "
        f"3 comparators = {len(llm_result.all_attempts)} attempts in {llm_result.runtime_seconds:.2f}s"
    )

    ablation_subset = cases[: args.ablation_robustness_n]
    ablation_results = run_ablations(ablation_subset, ontology, as_of_date=as_of_date)
    robustness_results = run_robustness(ablation_subset, ontology, as_of_date=as_of_date)
    print(
        f"Ablations: {len(ablation_results)} results over {len(ablation_subset)} cases. "
        f"Robustness: {len(robustness_results)} results over {len(ablation_subset)} cases."
    )

    write_checkpoint_b_outputs(
        output_dir=args.output,
        llm_result=llm_result,
        ablation_results=ablation_results,
        robustness_results=robustness_results,
        provider_dry_run=args.dry_run,
    )
    print(f"\nOutputs: {args.output}")


if __name__ == "__main__":
    main()
