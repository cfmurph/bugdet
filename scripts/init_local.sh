#!/usr/bin/env bash
# Create git-ignored local config and data folders. Safe to run repeatedly.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

copy_if_missing() {
  local src=$1 dst=$2
  if [[ -f "$dst" ]]; then
    echo "exists: $dst"
  else
    cp "$src" "$dst"
    echo "created: $dst  (edit with your numbers)"
  fi
}

copy_if_missing config/plan.example.yaml config/plan.yaml
copy_if_missing config/categories.example.yaml config/categories.yaml
copy_if_missing config/debts.example.yaml config/debts.yaml

mkdir -p data/raw data/processed reports
touch data/raw/.gitkeep data/processed/.gitkeep reports/.gitkeep

echo ""
echo "Next steps:"
echo "  1. Edit config/plan.yaml — income, debts, budget lines"
echo "  2. Drop bank CSV exports in data/raw/"
echo "  3. source .venv/bin/activate && jupyter lab"
