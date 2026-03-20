#!/bin/bash
echo "[SYSTEM] Initiating Cognitive Swarm Wake-Up Sequence..."

# 1. Safely patch the .env file to force dynamic MetaArchitect routing
if grep -q "^VERTEX_DEFAULT_MODEL=" .env; then
    sed -i 's/^VERTEX_DEFAULT_MODEL=/# VERTEX_DEFAULT_MODEL=/g' .env
    echo "[SYSTEM] Un-hardcoded VERTEX_DEFAULT_MODEL."
fi

# 2. Inject GCP credentials if missing
if ! grep -q "GOOGLE_APPLICATION_CREDENTIALS" .env; then
    echo "GOOGLE_APPLICATION_CREDENTIALS=/workspaces/tooloo-v2/too-loo-zi8g7e-755de9c9051a.json" >> .env
    echo "GCP_PROJECT_ID=too-loo-zi8g7e" >> .env
    echo "GCP_REGION=us-central1" >> .env
    echo "[SYSTEM] Injected ADC credentials into .env."
fi

# 3. Export live variables to the immediate shell
export GCP_PROJECT_ID="too-loo-zi8g7e"
export GCP_REGION="us-central1"
export GOOGLE_APPLICATION_CREDENTIALS="/workspaces/tooloo-v2/too-loo-zi8g7e-755de9c9051a.json"
export TOOLOO_LIVE_TESTS=1

# 4. Trigger the Fluid Crucible
echo "[SYSTEM] Igniting Live Inference. Executing Swarm Ouroboros Cycle 1..."
python3 run_cycles.py --cycles 1
