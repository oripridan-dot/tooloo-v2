#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="too-loo-zi8g7e"
SERVICE_NAME="buddys-chat"
REGION="me-west1"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

# Build container image using Cloud Build
# This replaces the local docker build/push with a remote Cloud Build
# It creates the image and pushes it to Artifact Registry in one step
# Requires that the Cloud Build API is enabled in the project

gcloud builds submit --tag "${IMAGE}" .

# Deploy to Cloud Run (protected, no unauthenticated access)
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --no-allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --set-env-vars "PORT=8080,USE_GCS=true,GCS_BUCKET=too-loo-zi8g7e,CLOUD_NATIVE_WORKSPACE=true,CHAT_DB_PATH=/tmp/sovereign_chat.db,CLOUD_NATIVE=true,ACTIVE_SOVEREIGN_REGION=me-west1,ACTIVE_SOVEREIGN_PROJECT=too-loo-zi8g7e"
