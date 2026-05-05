#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

bunx --bun @marp-team/marp-cli@latest zipmould.md \
  --pdf \
  --allow-local-files \
  --output zipmould.pdf
