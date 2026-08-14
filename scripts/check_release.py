#!/usr/bin/env python3
"""Run a conservative local pre-release audit.

The check is intentionally self-contained and uses temporary output directories.
It does not make live external API calls or launch the Streamlit server.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from kdaa import __version__  # noqa: E402
from kdaa.config import load_config  # noqa: E402
from kdaa.evaluation import run_robustness_suite, run_synthetic_benchmark  # noqa: E402
from kdaa.ingestion import build_demo_scenario, load_bundle  # noqa: E402
from kdaa.models import AnalysisRun  # noqa: E402
from kdaa.pipeline import KDAAPipeline  # noqa: E402

REQUIRED = [
    "README.md",
    "LICENSE",
    "CITATION.cff",
    "AI_USE_DISCLOSURE.md",
    "RELEASE_NOTES.md",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    "configs/default.yaml",
    "src/kdaa/models.py",
    "src/kdaa/ingestion/dedup.py",
    "src/kdaa/evaluation/robustness.py",
    "src/kdaa/pipeline.py",
    "app/streamlit_app.py",
    "examples/basic_usage.py",
    "scripts/package_release.py",
    "scripts/run_robustness.sh",
    "docs/architecture.md",
    "docs/theory_to_system.md",
    "docs/evaluation_protocol.md",
    "docs/release_checklist.md",
    "docs/assets/system_architecture.png",
    "docs/assets/theory_to_artifact.png",
    "docs/assets/benchmark_comparison.png",
    "docs/assets/robustness_signature.png",
    "docs/assets/robustness_score_deltas.png",
    "data/demo/synthetic_researcher.json",
    "data/demo/synthetic_lab.json",
    "data/demo/synthetic_team.json",
    "results/demo/analysis_run.json",
    "results/benchmark/benchmark_summary.json",
    "results/robustness/robustness_summary.json",
    "results/robustness/robustness_cases.csv",
]


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(SRC) if not existing else f"{SRC}{os.pathsep}{existing}"
    subprocess.run(command, cwd=ROOT, check=True, env=env)


def check_required() -> None:
    missing = [item for item in REQUIRED if not (ROOT / item).exists()]
    if missing:
        raise RuntimeError(f"Missing required release files: {missing}")


def check_structured_files() -> None:
    for path in ROOT.rglob("*.json"):
        if any(part in {".pytest_cache", ".git"} for part in path.parts):
            continue
        json.loads(path.read_text(encoding="utf-8"))
    for path in [ROOT / "configs/default.yaml", ROOT / "configs/conservative.yaml"]:
        yaml.safe_load(path.read_text(encoding="utf-8"))
        load_config(path)
    for path in sorted((ROOT / "data/demo").glob("synthetic_*.json")):
        bundle = load_bundle(path)
        if not bundle.unit.is_synthetic:
            raise RuntimeError(f"Demo is not marked synthetic: {path}")


def check_versions() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    if f'version = "{__version__}"' not in pyproject:
        raise RuntimeError("Package version mismatch in pyproject.toml")
    if f"version: {__version__}" not in citation:
        raise RuntimeError("Package version mismatch in CITATION.cff")


def check_committed_outputs() -> None:
    run_payload = AnalysisRun.model_validate_json(
        (ROOT / "results/demo/analysis_run.json").read_text(encoding="utf-8")
    )
    if run_payload.confirmed_assets:
        raise RuntimeError("Committed AI-only demo contains confirmed assets")
    expected_containers = {
        "repository",
        "living_document",
        "structured_knowledge_base",
        "deployable_product",
        "public_content",
    }
    actual = {item.output_container.value for item in run_payload.opportunities}
    if not expected_containers <= actual:
        raise RuntimeError(f"Missing output containers: {sorted(expected_containers - actual)}")

    benchmark = json.loads(
        (ROOT / "results/benchmark/benchmark_summary.json").read_text(encoding="utf-8")
    )
    if benchmark["kdaa_provenance_completeness"] != 1.0:
        raise RuntimeError("Committed benchmark lost complete provenance")
    if benchmark["kdaa_unsupported_claim_rate"] != 0.0:
        raise RuntimeError("Committed benchmark contains unsupported claims")
    if benchmark["kdaa_confirmed_without_human_rate"] != 0.0:
        raise RuntimeError("Committed benchmark confirms assets without human calibration")

    robustness = json.loads(
        (ROOT / "results/robustness/robustness_summary.json").read_text(encoding="utf-8")
    )
    if robustness["duplicate_signature_jaccard"] != 1.0:
        raise RuntimeError("Exact duplicate perturbation changed the committed asset signature")
    if robustness["duplicate_asset_count_delta"] != 0:
        raise RuntimeError("Exact duplicate perturbation inflated committed asset count")
    if robustness["stale_mean_credibility_delta"] >= 0:
        raise RuntimeError("Stale-evidence perturbation did not reduce credibility")
    if robustness["unknown_role_attribution_delta"] >= 0:
        raise RuntimeError("Unknown-role perturbation did not reduce attribution confidence")
    if robustness["irrelevant_noise_signature_jaccard"] != 1.0:
        raise RuntimeError("Irrelevant-noise perturbation changed the committed asset signature")
    if not robustness["all_cases_provenance_complete"]:
        raise RuntimeError("Committed robustness suite lost provenance completeness")
    if not robustness["all_cases_zero_auto_confirmation"]:
        raise RuntimeError("Committed robustness suite auto-confirmed an asset")


def check_markdown_links() -> None:
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    failures: list[str] = []
    for path in ROOT.rglob("*.md"):
        if any(part in {".git", ".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for target in pattern.findall(text):
            target = target.strip().strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            clean = target.split("#", 1)[0].split("?", 1)[0]
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            if not resolved.exists():
                failures.append(f"{path.relative_to(ROOT)} -> {target}")
    if failures:
        raise RuntimeError(f"Broken local Markdown links: {failures}")


def check_temp_runs() -> None:
    with tempfile.TemporaryDirectory(prefix="kdaa-release-") as temp:
        temp_path = Path(temp)
        for scenario in ("researcher", "lab", "team"):
            bundle = build_demo_scenario(scenario)
            run_payload, _ = KDAAPipeline().analyze(
                bundle, output_dir=temp_path / f"demo-{scenario}"
            )
            if run_payload.confirmed_assets:
                raise RuntimeError(f"{scenario} demo auto-confirmed an asset")
            AnalysisRun.model_validate_json(
                (temp_path / f"demo-{scenario}" / "analysis_run.json").read_text(
                    encoding="utf-8"
                )
            )

        benchmark, _ = run_synthetic_benchmark(
            n_units=10,
            seed=42,
            config=load_config(),
            output_dir=temp_path / "benchmark",
        )
        if benchmark.kdaa_provenance_completeness != 1.0:
            raise RuntimeError("Temporary benchmark lost provenance completeness")
        if benchmark.kdaa_confirmed_without_human_rate != 0.0:
            raise RuntimeError("Temporary benchmark auto-confirmed assets")

        robustness, _ = run_robustness_suite(
            config=load_config(),
            output_dir=temp_path / "robustness",
        )
        if robustness.duplicate_signature_jaccard != 1.0:
            raise RuntimeError("Temporary duplicate perturbation changed asset signature")
        if robustness.duplicate_asset_count_delta != 0:
            raise RuntimeError("Temporary duplicate perturbation inflated asset count")
        if robustness.stale_mean_credibility_delta >= 0:
            raise RuntimeError("Temporary stale perturbation did not reduce credibility")
        if robustness.unknown_role_attribution_delta >= 0:
            raise RuntimeError("Temporary unknown-role perturbation did not reduce attribution")
        if not robustness.all_cases_provenance_complete:
            raise RuntimeError("Temporary robustness suite lost provenance")
        if not robustness.all_cases_zero_auto_confirmation:
            raise RuntimeError("Temporary robustness suite auto-confirmed assets")


def check_secret_patterns() -> None:
    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ]
    allowed_suffixes = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt", ".example"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed_suffixes:
            continue
        if any(part in {".git", ".pytest_cache", "__pycache__"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                raise RuntimeError(f"Possible secret pattern in {path.relative_to(ROOT)}")


def main() -> None:
    check_required()
    check_structured_files()
    check_versions()
    check_markdown_links()
    check_committed_outputs()
    check_secret_patterns()
    run([sys.executable, "-m", "compileall", "-q", "src", "app", "scripts", "tests", "examples"])
    run([sys.executable, "-m", "pytest", "-q"])
    check_temp_runs()
    print(f"Release audit passed for KDAA-AI {__version__}.")


if __name__ == "__main__":
    main()
