# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining check_vertex_diagnostic.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.393123
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import os
import sys
from pathlib import Path

# Repo root
_REPO = Path("/Users/oripridan/ANTIGRAVITY/tooloo-v2")
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from engine.config import settings

print(f"GCP Project ID: {settings.gcp_project_id}")
print(f"GCP Region: {settings.gcp_region}")
print(f"Vertex Available: {settings.vertex_available}")
print(f"Gemini API Key: {'***' if settings.gemini_api_key else 'None'}")
print(f"OpenAI API Key: {'***' if settings.openai_api_key else 'None'}")

if not settings.gcp_project_id:
    print("WARNING: GCP_PROJECT__ID is not set in .env or environment.")
else:
    print("GCP_PROJECT_ID is set.")

env_path = _REPO / ".env"
if env_path.exists():
    print(f".env exists at {env_path}")
    content = env_path.read_text()
    if "GCP_PROJECT_ID" in content:
         print("GCP_PROJECT_ID found in .env file.")
    else:
         print("GCP_PROJECT_ID NOT found in .env file.")
else:
    print(f".env does NOT exist at {env_path}")
