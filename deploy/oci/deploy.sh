#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${ENV_FILE:-/etc/zipmould-viz.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

REPO_DIR="${ZIPMOULD_REPO_DIR:-/opt/zipmould/slime-mould}"
BRANCH="${ZIPMOULD_BRANCH:-main}"
BUILD_FRONTEND="${BUILD_FRONTEND:-0}"

cd "$REPO_DIR"

git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

uv sync --extra viz

if [[ "$BUILD_FRONTEND" == "1" ]]; then
  if ! command -v bun >/dev/null 2>&1; then
    echo "BUILD_FRONTEND=1 requires bun on the VM." >&2
    exit 1
  fi
  (cd viz-web && bun install --frozen-lockfile && bun run build)
fi

sudo systemctl restart zipmould-viz
sudo systemctl status zipmould-viz --no-pager
