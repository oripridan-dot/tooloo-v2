#!/usr/bin/env bash
# deploy.sh — TooLoo V4 Sovereign Hub: One-command local → Cloud Run deploy
# Usage:  ./deploy.sh            (full deploy)
#         ./deploy.sh --dry-run  (print steps, execute nothing)
# Governed by Rule 0 (Brutal Honesty): every step reports its real outcome.
set -euo pipefail

# ── Config (override via env or .env) ────────────────────────────────────────
source .env 2>/dev/null || true

PROJECT_ID="${GCP_PROJECT_ID:-too-loo-zi8g7e}"
REGION="${GCP_REGION:-me-west1}"
SERVICE="tooloo-v4-hub"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE}:$(git rev-parse --short HEAD 2>/dev/null || echo latest)"
GCS_BUCKET="${PERSISTENT_STORAGE_URL:-gs://too-loo-workspace-v4-too-loo-zi8g7e}"
DRY_RUN=false

# Resolve gcloud if not on PATH (common on macOS when script runs outside login shell)
if ! command -v gcloud &>/dev/null; then
  for candidate in \
    /opt/homebrew/share/google-cloud-sdk/bin/gcloud \
    /usr/local/share/google-cloud-sdk/bin/gcloud \
    "$HOME/google-cloud-sdk/bin/gcloud" \
    /usr/lib/google-cloud-sdk/bin/gcloud; do
    if [[ -x "$candidate" ]]; then
      export PATH="$(dirname "$candidate"):$PATH"
      break
    fi
  done
fi

if ! command -v gcloud &>/dev/null; then
  echo "ERROR: gcloud not found. Install from https://cloud.google.com/sdk/docs/install"
  exit 1
fi

for arg in "$@"; do
  [[ "$arg" == "--dry-run" ]] && DRY_RUN=true
done

run() {
  echo "  ▶ $*"
  $DRY_RUN || eval "$*"
}

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  TooLoo V4 — Sovereign Deploy Pipeline                  ║"
echo "║  Project: ${PROJECT_ID}   Region: ${REGION}             ║"
$DRY_RUN && echo "║  MODE: DRY-RUN (no changes will be made)                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Auth check ────────────────────────────────────────────────────────
echo "[1/5] Verifying gcloud auth..."
if ! gcloud auth print-identity-token &>/dev/null; then
  echo "ERROR: Not authenticated. Run: gcloud auth login && gcloud auth configure-docker"
  exit 1
fi
echo "  ✓ Auth OK (project: ${PROJECT_ID})"

# ── Step 2: Sync knowledge_lessons.json to GCS (cloud gets local lessons) ────
echo "[2/5] Syncing KnowledgeBank to cloud storage..."
if [[ -f "knowledge_lessons.json" ]]; then
  run "gsutil cp knowledge_lessons.json ${GCS_BUCKET}/knowledge_lessons.json"
  echo "  ✓ KnowledgeBank synced → ${GCS_BUCKET}/knowledge_lessons.json"
else
  echo "  ⚠ knowledge_lessons.json not found — skipping sync"
fi

# ── Step 3+4: Build (via Cloud Build) and deploy to Cloud Run ─────────────────
# Uses gcloud run deploy --source which builds the image on GCP via Cloud Build.
# No local Docker required.
echo "[3/5] Building via Cloud Build and deploying to Cloud Run..."
run "gcloud run deploy ${SERVICE} \
  --source=. \
  --project=${PROJECT_ID} \
  --region=${REGION} \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3 \
  --set-env-vars=GEMINI_API_KEY=${GEMINI_API_KEY:-},GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},CLOUD_NATIVE_WORKSPACE=true,GCS_KNOWLEDGE_PATH=${GCS_BUCKET}/knowledge_lessons.json,CLOUD_HUB_URL=https://tooloo-v4-hub-gru3xdvw6a-uc.a.run.app \
  --quiet"

# ── Step 5: Health check ──────────────────────────────────────────────────────
echo "[5/5] Running health check..."
if ! $DRY_RUN; then
  CLOUD_URL=$(gcloud run services describe "${SERVICE}" \
    --project="${PROJECT_ID}" --region="${REGION}" \
    --format="value(status.url)" 2>/dev/null || echo "")
  
  if [[ -n "${CLOUD_URL}" ]]; then
    echo "  Live URL: ${CLOUD_URL}"
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${CLOUD_URL}/health" --max-time 15 || echo "000")
    if [[ "${HTTP_STATUS}" == "200" ]]; then
      echo "  ✓ Health check PASSED (HTTP ${HTTP_STATUS})"
      echo ""
      echo "╔══════════════════════════════════════════════════════════╗"
      echo "║  ✅ DEPLOY SUCCESS                                       ║"
      echo "║  URL: ${CLOUD_URL}"
      echo "╚══════════════════════════════════════════════════════════╝"
    else
      echo "  ✗ Health check FAILED (HTTP ${HTTP_STATUS}) — check Cloud Run logs"
      exit 1
    fi
  else
    echo "  ⚠ Could not retrieve service URL — check Cloud Run console"
  fi
else
  echo "  [DRY-RUN] Would check health at Cloud Run URL"
  echo ""
  echo "╔══════════════════════════════════════════════════════════╗"
  echo "║  DRY-RUN COMPLETE — no changes made                      ║"
  echo "╚══════════════════════════════════════════════════════════╝"
fi
