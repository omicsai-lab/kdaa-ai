#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"
rm -rf results/benchmark
python -m kdaa benchmark --n-units 50 --seed 42 --output results/benchmark
python scripts/build_figures.py
