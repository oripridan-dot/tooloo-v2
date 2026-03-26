#!/usr/bin/env bash
# run_ui.sh — Launch TooLoo V2 Streamlit Frontend
# Usage: bash run_ui.sh

set -euo pipefail
UI_PORT="${STUDIO_UI_PORT:-8501}"
API_URL="${TOOLOO_API_URL:-http://localhost:8002}"

echo "[TooLoo UI] Starting Streamlit on port $UI_PORT connecting to API at $API_URL"
export TOOLOO_API_URL="$API_URL"
./.venv/bin/streamlit run src/ui/app.py --server.port "$UI_PORT" --server.address 0.0.0.0
