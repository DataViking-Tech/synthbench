#!/usr/bin/env bash
# Mirrors the CI `lint` job. Polecats run this before `gt done` to avoid
# shipping a branch that fails CI formatting checks.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

if command -v ruff >/dev/null 2>&1; then
    RUFF=(ruff)
elif command -v python3 >/dev/null 2>&1 && python3 -m ruff --version >/dev/null 2>&1; then
    RUFF=(python3 -m ruff)
elif command -v python >/dev/null 2>&1 && python -m ruff --version >/dev/null 2>&1; then
    RUFF=(python -m ruff)
else
    echo "format-check: ruff not found. Install with 'pip install ruff'." >&2
    exit 1
fi

echo "ruff check ."
"${RUFF[@]}" check .

echo "ruff format --check ."
"${RUFF[@]}" format --check .
