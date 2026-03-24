#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"

exec python3.12 -m uvicorn jarvis_ai_workbench.app:app --host 0.0.0.0 --port "${PORT:-8010}" --reload
