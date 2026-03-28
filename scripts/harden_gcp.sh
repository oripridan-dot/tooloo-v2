#!/bin/zsh
set -e

PROJECT_ID="too-loo-zi8g7e"
echo "--- HARDENING GCP INFRASTRUCTURE: ${PROJECT_ID} ---"

# 1. Ensure gcloud is configured to the correct project
gcloud config set project "${PROJECT_ID}"

# 2. Force-enable critical APIs (Rule 4 Compliance)
echo "[1/3] Enabling Service Usage API..."
gcloud services enable serviceusage.googleapis.com

echo "[2/3] Enabling Cloud Run API..."
gcloud services enable run.googleapis.com

echo "[3/3] Enabling Artifact Registry API..."
gcloud services enable artifactregistry.googleapis.com

# 3. Audit Active Services
echo "\n--- ACTIVE SOTA SERVICES ---"
gcloud services list --enabled --filter="name:*.googleapis.com"

echo "\nInfrastructure Hardened. Uninterrupted access restored."
