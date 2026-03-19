#!/usr/bin/env bash
# setup_gcp_key.sh — Wire the TooLoo service account key into the pipeline.
# Run once after dropping tooloo-sa-key.json into the workspace root.
#
# Usage:
#   1. In Google Cloud Console → IAM & Admin → Service Accounts
#      → tooloo-core-sa@too-loo-zi8g7e.iam.gserviceaccount.com
#      → Keys → Add Key → JSON → save as:
#         /workspaces/tooloo-v2/tooloo-sa-key.json
#
#   2. Then run:  bash setup_gcp_key.sh

set -euo pipefail

KEY="/workspaces/tooloo-v2/tooloo-sa-key.json"
PROJECT="too-loo-zi8g7e"
SA="tooloo-core-sa@too-loo-zi8g7e.iam.gserviceaccount.com"

echo "── TooLoo GCP Key Setup ─────────────────────────────────────"

# 1. Check key file exists
if [[ ! -f "$KEY" ]]; then
  echo ""
  echo " KEY FILE MISSING — download it first:"
  echo ""
  echo "  1. Open: https://console.cloud.google.com/iam-admin/serviceaccounts/details/$SA/keys?project=$PROJECT"
  echo "  2. Click 'Add Key' → 'Create new key' → JSON → Create"
  echo "  3. Save the downloaded file as: $KEY"
  echo ""
  exit 1
fi

echo "✓ Key file found: $KEY"

# 2. Validate JSON is parseable
python3 -c "import json, sys; d=json.load(open('$KEY')); print('✓ Key type:', d.get('type')); print('✓ SA email:', d.get('client_email'))" || {
  echo "✗ Key file is not valid JSON"; exit 1
}

# 3. Ensure GOOGLE_APPLICATION_CREDENTIALS is in .env
ENV_FILE="/workspaces/tooloo-v2/.env"
if grep -q "^GOOGLE_APPLICATION_CREDENTIALS=" "$ENV_FILE"; then
  echo "✓ GOOGLE_APPLICATION_CREDENTIALS already in .env"
else
  echo "GOOGLE_APPLICATION_CREDENTIALS=$KEY" >> "$ENV_FILE"
  echo "✓ Added GOOGLE_APPLICATION_CREDENTIALS to .env"
fi

# 4. Export for this shell session
export GOOGLE_APPLICATION_CREDENTIALS="$KEY"
echo "✓ Exported GOOGLE_APPLICATION_CREDENTIALS for this session"

# 5. Verify ADC resolves
echo ""
echo "── Verifying credentials ────────────────────────────────────"
python3 - <<'PYEOF'
import os, sys
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/workspaces/tooloo-v2/tooloo-sa-key.json")
sys.path.insert(0, "/workspaces/tooloo-v2")

import google.auth
creds, project = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
print(f"✓ ADC resolved — project: {project}")
print(f"✓ Creds type:             {type(creds).__name__}")
PYEOF

# 6. Smoke-test Vertex AI init
echo ""
echo "── Smoke-testing Vertex AI ──────────────────────────────────"
python3 - <<'PYEOF'
import os, sys, warnings
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "/workspaces/tooloo-v2/tooloo-sa-key.json")
sys.path.insert(0, "/workspaces/tooloo-v2")

import vertexai
vertexai.init(project="too-loo-zi8g7e", location="us-central1")

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from vertexai.generative_models import GenerativeModel

model = GenerativeModel("gemini-2.5-flash")
resp = model.generate_content("Reply with exactly: VERTEX_LIVE")
print(f"✓ Vertex response: {resp.text.strip()}")
print()
print("══════════════════════════════════════════════════════════════")
print("  TooLoo pipeline is now routed through Vertex AI Model Garden")
print(f"  Project : too-loo-zi8g7e")
print(f"  Region  : us-central1")
print(f"  SA      : tooloo-core-sa@too-loo-zi8g7e.iam.gserviceaccount.com")
print("══════════════════════════════════════════════════════════════")
PYEOF
