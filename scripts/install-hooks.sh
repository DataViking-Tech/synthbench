#!/usr/bin/env bash
# Opt-in installer: point this clone's git at the repo-tracked hooks in .githooks/.
# Running this once per clone enables the pre-push ruff format check.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

git config core.hooksPath .githooks
echo "Hooks enabled: core.hooksPath -> .githooks"
echo "Installed hooks:"
ls -1 .githooks/ | sed 's/^/  - /'
echo
echo "Disable later with: git config --unset core.hooksPath"
