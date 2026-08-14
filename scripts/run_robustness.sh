#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"
rm -rf results/robustness
python -m kdaa stress-test --output results/robustness
python scripts/build_figures.py
