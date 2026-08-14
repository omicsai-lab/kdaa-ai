#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="${PYTHONPATH:-}:$ROOT/src"
rm -rf results/demo results/demo-lab results/demo-team
python -m kdaa demo --scenario researcher --output results/demo
python -m kdaa demo --scenario lab --output results/demo-lab
python -m kdaa demo --scenario team --output results/demo-team
