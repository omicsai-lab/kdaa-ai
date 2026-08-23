"""Dry validation for the Paper B final evaluation freeze -- no live calls, no case
generation. Confirms the frozen final-study configuration parses and is internally
consistent, computes the locked source-hash manifest, and confirms no final case data
exists yet. See docs/paper_b_final_evaluation_freeze.md.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from kdaa.evaluation.paper_b.boundary import find_truth_leakage  # noqa: E402

CONFIG_DIR = REPO_ROOT / "configs" / "paper_b"

HASH_TARGETS: dict[str, Path] = {
    "final_model_lock.yaml": CONFIG_DIR / "final_model_lock.yaml",
    "final_experiment_lock.yaml": CONFIG_DIR / "final_experiment_lock.yaml",
    "final_scorer_lock.yaml": CONFIG_DIR / "final_scorer_lock.yaml",
    "experiment_lock.yaml (WP0 baseline)": CONFIG_DIR / "experiment_lock.yaml",
    "C1 prompt (c1_generic_llm.py)": SRC_ROOT / "kdaa/evaluation/paper_b/adapters/c1_generic_llm.py",
    "C2 prompt (c2_evidence_linked.py)": SRC_ROOT / "kdaa/evaluation/paper_b/adapters/c2_evidence_linked.py",
    "C4 production LLM prompt (discovery/llm.py)": SRC_ROOT / "kdaa/discovery/llm.py",
    "C4 adapter wrapper (c4_hybrid.py)": SRC_ROOT / "kdaa/evaluation/paper_b/adapters/c4_hybrid.py",
    "shared LLM harness/schema/retry policy (llm_harness.py)": SRC_ROOT
    / "kdaa/evaluation/paper_b/adapters/llm_harness.py",
    "ontology (ontology.yaml)": SRC_ROOT / "kdaa/resources/ontology.yaml",
    "subset-selection algorithm (dev_llm_subset.py)": SRC_ROOT / "kdaa/evaluation/paper_b/dev_llm_subset.py",
    "paired bootstrap analysis (analysis.py)": SRC_ROOT / "kdaa/evaluation/paper_b/analysis.py",
}


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_directory(path: Path) -> str:
    """Concatenated, path-sorted content hash over every .py file in a directory tree --
    used for the scoring/ package, which has multiple files."""
    digest = hashlib.sha256()
    for file_path in sorted(path.rglob("*.py")):
        digest.update(str(file_path.relative_to(REPO_ROOT)).encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    failures: list[str] = []
    print("=== Paper B final freeze -- dry validation (no live calls, no case generation) ===\n")

    # 1. The final configuration parses.
    configs: dict[str, dict] = {}
    for name in ("final_model_lock.yaml", "final_experiment_lock.yaml", "final_scorer_lock.yaml"):
        path = CONFIG_DIR / name
        try:
            configs[name] = yaml.safe_load(path.read_text(encoding="utf-8"))
            print(f"[OK] {name} parses")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name} failed to parse: {exc}")
            print(f"[FAIL] {name}: {exc}")

    exp = configs.get("final_experiment_lock.yaml", {})

    # 2. Expected case counts are 180 + 60.
    dataset = exp.get("final_dataset", {})
    core_n, challenge_n, total_n = dataset.get("core_n"), dataset.get("challenge_n"), dataset.get("total_n")
    if (core_n, challenge_n, total_n) == (180, 60, 240) and core_n + challenge_n == total_n:
        print(f"[OK] final dataset counts: {core_n} core + {challenge_n} challenge = {total_n}")
    else:
        failures.append(f"final dataset counts wrong: core={core_n} challenge={challenge_n} total={total_n}")
        print(f"[FAIL] final dataset counts: core={core_n} challenge={challenge_n} total={total_n}")

    # 3. LLM subset design is 30 core + 30 challenge.
    subset = exp.get("final_llm_subset", {})
    s_core, s_challenge, s_n = subset.get("core_n"), subset.get("challenge_n"), subset.get("n")
    if (s_core, s_challenge, s_n) == (30, 30, 60) and s_core + s_challenge == s_n:
        print(f"[OK] final LLM subset: {s_core} core + {s_challenge} challenge = {s_n}")
    else:
        failures.append(f"final LLM subset wrong: core={s_core} challenge={s_challenge} n={s_n}")
        print(f"[FAIL] final LLM subset: core={s_core} challenge={s_challenge} n={s_n}")

    # 4. Intended LLM calls calculate to 540.
    repeats = subset.get("intended_repeats_per_case")
    comparators = subset.get("comparators", [])
    intended_calls = subset.get("intended_primary_live_llm_calls")
    computed_calls = (s_n or 0) * (repeats or 0) * len(comparators)
    if intended_calls == 540 and computed_calls == 540:
        print(f"[OK] intended primary live LLM calls: {s_n} x {repeats} x {len(comparators)} = {computed_calls}")
    else:
        failures.append(f"intended LLM call count wrong: recorded={intended_calls} computed={computed_calls}")
        print(f"[FAIL] intended LLM call count: recorded={intended_calls} computed={computed_calls}")

    # 5. Prompts/configs/scorers hash successfully.
    print("\n--- Locked source hash manifest (sha256) ---")
    hash_manifest: dict[str, str] = {}
    for label, target in HASH_TARGETS.items():
        try:
            digest = _sha256_directory(target) if target.is_dir() else _sha256_file(target)
            hash_manifest[label] = digest
            print(f"  {digest}  {label}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"failed to hash {label} ({target}): {exc}")
            print(f"[FAIL] could not hash {label}: {exc}")

    scoring_dir = SRC_ROOT / "kdaa/evaluation/paper_b/scoring"
    try:
        scoring_hash = _sha256_directory(scoring_dir)
        hash_manifest["scorer package (scoring/, all files)"] = scoring_hash
        print(f"  {scoring_hash}  scorer package (scoring/, all files)")
    except Exception as exc:  # noqa: BLE001
        failures.append(f"failed to hash scoring/ directory: {exc}")
        print(f"[FAIL] could not hash scoring/: {exc}")

    if len(hash_manifest) == len(HASH_TARGETS) + 1:
        print(f"[OK] all {len(hash_manifest)} targets hashed successfully")
    else:
        print(f"[FAIL] only {len(hash_manifest)}/{len(HASH_TARGETS) + 1} targets hashed")

    # 6. Truth/inference isolation still passes.
    print("\n--- Truth/inference boundary check ---")
    violations = find_truth_leakage()
    if not violations:
        print("[OK] no direct truth-module import across any inference boundary namespace")
    else:
        failures.append(f"truth leakage detected: {violations}")
        print(f"[FAIL] truth leakage detected: {violations}")

    # 7. No final case has been generated.
    print("\n--- Final case generation status ---")
    final_evidence_dir = REPO_ROOT / "data" / "synthetic" / "final_evidence"
    final_truth_dir = REPO_ROOT / "data" / "synthetic" / "final_truth"
    for label, d in (("final_evidence", final_evidence_dir), ("final_truth", final_truth_dir)):
        if not d.exists():
            print(f"[OK] {label} directory does not exist yet -- no final cases generated")
        elif not any(d.iterdir()):
            print(f"[OK] {label} directory exists but is empty -- no final cases generated")
        else:
            failures.append(f"{label} directory is non-empty: {d}")
            print(f"[FAIL] {label} directory is NOT empty: {d}")

    print("\n=== Summary ===")
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("All dry-validation checks passed. No live API call made. No final case generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
