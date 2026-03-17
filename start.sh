#!/usr/bin/env bash
# start.sh — Launch TooLoo V2 on port 8000 with auto-restart on crash.
# Usage: bash start.sh
set -euo pipefail
PORT="${TOOLOO_PORT:-8000}"
LOGFILE="${TOOLOO_LOG:-/tmp/tooloo.log}"
MAX_RESTARTS=99
count=0
echo "[TooLoo] Starting on port $PORT  →  log: $LOGFILE"
while [ $count -lt $MAX_RESTARTS ]; do
  echo "[TooLoo] Launch attempt $((count+1))  $(date -u +%H:%M:%S)" >> "$LOGFILE"
  python -m uvicorn studio.api:app \
    --host 0.0.0.0 \
    --port "$PORT" \
    --workers 1 \
    --log-level info \
    2>&1 | tee -a "$LOGFILE" || true
  count=$((count+1))
  echo "[TooLoo] Process exited — restarting in 3 s…" | tee -a "$LOGFILE"
  sleep 3
done
echo "[TooLoo] Max restarts reached." | tee -a "$LOGFILE"
