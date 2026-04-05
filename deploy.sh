#!/usr/bin/env bash
# deploy.sh — TooLoo Sovereign Hub: ONE command to deploy
# Usage:  ./deploy.sh            (deploy buddys-chat to cloud)
#         ./deploy.sh --dry-run  (print what would happen)
# Governed by Rule 0 (Brutal Honesty): every step reports its real outcome.
set -euo pipefail

source .env 2>/dev/null || true

# ── Single source of truth ────────────────────────────────────────────────────
PROJECT="${GCP_PROJECT_ID:-too-loo-zi8g7e}"
REGION="me-west1"          # ONE region
SERVICE="buddys-chat"       # ONE service
CHAT_URL="https://buddys-chat-gru3xdvw6a-zf.a.run.app"
GCS_BUCKET="${PERSISTENT_STORAGE_URL:-gs://too-loo-workspace-v4-too-loo-zi8g7e}"
DRY_RUN=false

# Resolve gcloud
if ! command -v gcloud &>/dev/null; then
  for candidate in \
    /opt/homebrew/share/google-cloud-sdk/bin/gcloud \
    /usr/local/share/google-cloud-sdk/bin/gcloud \
    "$HOME/google-cloud-sdk/bin/gcloud" \
    /usr/lib/google-cloud-sdk/bin/gcloud; do
    [[ -x "$candidate" ]] && export PATH="$(dirname "$candidate"):$PATH" && break
  done
fi
command -v gcloud &>/dev/null || { echo "ERROR: gcloud not found"; exit 1; }

for arg in "$@"; do [[ "$arg" == "--dry-run" ]] && DRY_RUN=true; done

run() { echo "  ▶ $*"; $DRY_RUN || eval "$*"; }

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  TooLoo — Deploy to Cloud                           ║"
echo "║  Service: ${SERVICE}                                ║"
echo "║  Project: ${PROJECT} / Region: ${REGION}           ║"
$DRY_RUN && echo "║  DRY-RUN MODE                                        ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Step 1: Auth
echo "[1/3] Checking auth..."
gcloud auth print-identity-token &>/dev/null || {
  echo "ERROR: Not authenticated. Run: gcloud auth login"
  exit 1
}
echo "  ✓ Authenticated"

# Step 2: Sync knowledge to GCS
echo "[2/3] Syncing knowledge to cloud..."
[[ -f "knowledge_lessons.json" ]] && run "gsutil cp knowledge_lessons.json ${GCS_BUCKET}/knowledge_lessons.json" && echo "  ✓ Synced" || echo "  ⚠ No knowledge_lessons.json — skipped"

# Step 3: Build + Deploy
echo "[3/3] Building and deploying (this takes ~3 minutes)..."
run "gcloud run deploy ${SERVICE} \
  --source=. \
  --project=${PROJECT} \
  --region=${REGION} \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars=GEMINI_API_KEY=${GEMINI_API_KEY:-},GCP_PROJECT_ID=${PROJECT},GCP_REGION=${REGION},CLOUD_NATIVE_WORKSPACE=true,GCS_KNOWLEDGE_PATH=${GCS_BUCKET}/knowledge_lessons.json \
  --quiet"

if ! $DRY_RUN; then
  HTTP=$(curl -s -o /dev/null -w "%{http_code}" "${CHAT_URL}/health" --max-time 15 || echo "000")
  echo ""
  if [[ "$HTTP" == "200" ]]; then
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║  ✅ DEPLOYED                                         ║"
    echo "║  Chat: ${CHAT_URL}/portal/index.html  ║"
    echo "╚══════════════════════════════════════════════════════╝"
  else
    echo "  ✗ Health check failed (HTTP ${HTTP}) — check: gcloud run logs ${SERVICE} --region=${REGION}"
    exit 1
  fi
fi
