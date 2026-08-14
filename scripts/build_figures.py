#!/usr/bin/env python3
"""Regenerate documentation diagrams and the synthetic benchmark chart."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
BENCHMARK = ROOT / "results" / "benchmark" / "benchmark_summary.json"
ROBUSTNESS = ROOT / "results" / "robustness" / "robustness_summary.json"


def render_graphviz() -> None:
    for source in sorted(ASSETS.glob("*.dot")):
        for fmt in ("svg", "png"):
            command = ["dot", f"-T{fmt}"]
            if fmt == "png":
                command.extend(["-Gdpi=180"])
            command.extend([str(source), "-o", str(source.with_suffix(f'.{fmt}'))])
            subprocess.run(command, check=True)


def benchmark_chart() -> None:
    payload = json.loads(BENCHMARK.read_text(encoding="utf-8"))
    labels = [
        "Concept\nprecision",
        "Concept\nrecall",
        "Concept\nF1",
        "Provenance\ncompleteness",
        "Supported\nclaim rate",
    ]
    baseline = [
        payload["baseline_concept_precision"],
        payload["baseline_concept_recall"],
        payload["baseline_concept_f1"],
        payload["baseline_provenance_completeness"],
        1.0 - payload["baseline_unsupported_claim_rate"],
    ]
    kdaa = [
        payload["kdaa_concept_precision"],
        payload["kdaa_concept_recall"],
        payload["kdaa_concept_f1"],
        payload["kdaa_provenance_completeness"],
        1.0 - payload["kdaa_unsupported_claim_rate"],
    ]

    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(11.5, 5.8))
    baseline_bars = ax.bar(x - width / 2, baseline, width, label="Flat-profile baseline")
    kdaa_bars = ax.bar(x + width / 2, kdaa, width, label="KDAA deterministic pipeline")
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Score (0–1)")
    ax.set_title(
        f"Controlled synthetic engineering benchmark (n={payload['n_units']}, seed={payload['seed']})"
    )
    ax.set_xticks(x, labels)
    ax.legend(loc="upper left", ncols=2)
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.bar_label(baseline_bars, fmt="%.2f", padding=3, fontsize=9)
    ax.bar_label(kdaa_bars, fmt="%.2f", padding=3, fontsize=9)
    ax.text(
        0.01,
        -0.20,
        "Synthetic software-validation result only. It does not validate latent knowledge assets, "
        "human usefulness, or realized value.",
        transform=ax.transAxes,
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(ASSETS / "benchmark_comparison.png", dpi=220, bbox_inches="tight")
    fig.savefig(ASSETS / "benchmark_comparison.svg", bbox_inches="tight")
    plt.close(fig)


def robustness_signature_chart() -> None:
    payload = json.loads(ROBUSTNESS.read_text(encoding="utf-8"))
    labels = [
        "Duplicate traces",
        "Stale dates",
        "Unknown roles",
        "One trace removed",
        "Irrelevant noise",
    ]
    values = [
        payload["duplicate_signature_jaccard"],
        payload["stale_signature_jaccard"],
        payload["unknown_role_signature_jaccard"],
        payload["dropped_trace_signature_jaccard"],
        payload["irrelevant_noise_signature_jaccard"],
    ]

    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    bars = ax.barh(np.arange(len(labels)), values)
    ax.set_xlim(0, 1.08)
    ax.set_xlabel("Asset-signature Jaccard similarity to unperturbed run")
    ax.set_title("Deterministic perturbation suite: structural stability")
    ax.set_yticks(np.arange(len(labels)), labels)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.bar_label(bars, fmt="%.2f", padding=4, fontsize=9)
    ax.text(
        0.0,
        -0.18,
        "Synthetic engineering result. Exact/source-record-equivalent duplicates are retained but de-weighted from analysis.",
        transform=ax.transAxes,
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(ASSETS / "robustness_signature.png", dpi=220, bbox_inches="tight")
    fig.savefig(ASSETS / "robustness_signature.svg", bbox_inches="tight")
    plt.close(fig)


def robustness_delta_chart() -> None:
    payload = json.loads(ROBUSTNESS.read_text(encoding="utf-8"))
    labels = [
        "Duplicate traces:\nmean credibility",
        "Stale dates:\nmean credibility",
        "Unknown roles:\nmean attribution",
    ]
    values = [
        payload["duplicate_mean_credibility_delta"],
        payload["stale_mean_credibility_delta"],
        payload["unknown_role_attribution_delta"],
    ]

    fig, ax = plt.subplots(figsize=(9.6, 5.8))
    bars = ax.bar(np.arange(len(labels)), values)
    lower = min(-0.70, min(values) - 0.08)
    upper = max(0.08, max(values) + 0.08)
    ax.set_ylim(lower, upper)
    ax.axhline(0.0, linewidth=1.0)
    ax.set_ylabel("Mean score change from unperturbed run")
    ax.set_title("Deterministic perturbation suite: expected directional response")
    ax.set_xticks(np.arange(len(labels)), labels)
    ax.grid(axis="y", alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    labels_for_bars = [f"{value:+.3f}" for value in values]
    ax.bar_label(bars, labels=labels_for_bars, padding=4, fontsize=9)
    ax.text(
        0.0,
        -0.20,
        "Staleness and attribution perturbations affect declared score components without confirming or rejecting assets.",
        transform=ax.transAxes,
        fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(ASSETS / "robustness_score_deltas.png", dpi=220, bbox_inches="tight")
    fig.savefig(ASSETS / "robustness_score_deltas.svg", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    render_graphviz()
    benchmark_chart()
    robustness_signature_chart()
    robustness_delta_chart()
