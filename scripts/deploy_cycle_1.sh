#!/bin/bash
# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: DEPLOY_CYCLE_1.SH | Version: 1.0.0
# WHERE: scripts/deploy_cycle_1.sh
# WHY: Rule 18 - Sovereign Cloud-Native Manifestation
# HOW: GCloud Build & Run (Cycle 1: The Real Brain)
# ==========================================================

set -e

PROJECT_ID="too-loo-zi8g7e"
REGION="me-west1"
SERVICE_NAME="tooloo-memory-organ"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:v4.2.0"

echo "🚀 Sovereign Evolution Pulse: Initiating Cycle 1 Cloud Deployment..."

# 1. Auth check
if [ -f "service-account.json" ]; then
    echo "🔑 Authenticating with Sovereign Service Account..."
    gcloud auth activate-service-account --key-file=service-account.json
    gcloud config set project $PROJECT_ID
else
    echo "⚠️  Authentication Error: service-account.json not found in root. Proceeding with active credentials."
fi

# 2. Build in Cloud Build
echo "🏗️  Building Container: ${IMAGE_TAG}..."
gcloud builds submit --tag $IMAGE_TAG ./tooloo_v4_hub/organs/memory_organ/

# 3. Deploy to Cloud Run
echo "🌩️  Deploying to Cloud Run (${REGION})..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_TAG \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars "CLOUD_NATIVE=true,ACTIVE_SOVEREIGN_PROJECT=${PROJECT_ID},ACTIVE_SOVEREIGN_REGION=${REGION}"

echo "✅ Cycle 1 Deployment SUCCESS."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format='value(status.url)')
echo "🌐 Sovereign Endpoint Live at: ${SERVICE_URL}"

# 4. Ready Check
echo "🔍 Performing High-Fidelity Ready Check (Rule 16)..."
curl -s -H "X-Sovereign-Key: SOVEREIGN_HUB_2026_V3" "${SERVICE_URL}/health" | grep -q "SOVEREIGN"
echo "✨ Status: REAL AND KICKING."
