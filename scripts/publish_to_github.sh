#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REPO="omicsai-lab/kdaa-ai"
MODE="${1:---dry-run}"

cat <<MSG
Target: https://github.com/$REPO
Mode:   $MODE

This helper never uploads unless called with --push.
It assumes the GitHub CLI is installed and authenticated with permission to the OmicsAI organization.
MSG

python scripts/check_release.py

if [[ "$MODE" != "--push" ]]; then
  echo
  echo "Dry run complete. To initialize, commit, create/push the repository, run:"
  echo "  scripts/publish_to_github.sh --push"
  exit 0
fi

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v gh >/dev/null || { echo "GitHub CLI (gh) is required" >&2; exit 1; }
gh auth status

if [[ ! -d .git ]]; then
  git init -b main
fi

git add .
if ! git diff --cached --quiet; then
  git commit -m "Initial KDAA-AI research MVP v0.1.0"
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "https://github.com/$REPO.git"
  git push -u origin main
else
  if gh repo view "$REPO" >/dev/null 2>&1; then
    git remote add origin "https://github.com/$REPO.git"
    git push -u origin main
  else
    gh repo create "$REPO" --public --source=. --remote=origin --push \
      --description "Provenance-aware knowledge asset discovery, assessment, and amplification research platform"
  fi
fi

echo "Published to https://github.com/$REPO"
