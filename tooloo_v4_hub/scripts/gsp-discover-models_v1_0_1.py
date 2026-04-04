# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_GSP-DISCOVER-MODELS.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/scripts/gsp-discover-models.py
# WHEN: 2026-04-04T00:41:42.466117+00:00
# WHY: Heal STAMP_PURITY_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import os
import sys
from typing import List, Dict, Any

# Ensure project context is loaded
PROJECT_ID = os.getenv("ACTIVE_SOVEREIGN_PROJECT", "tooloo-v4-sovereign-104845")
REGION = os.getenv("ACTIVE_SOVEREIGN_REGION", "me-west1")

def discover_models():
    print(f"--- 🛰️ SOTA Discovery Pulse: {PROJECT_ID} @ {REGION} ---")
    
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
        vertexai.init(project=PROJECT_ID, location=REGION)
        
        # We manually test the most likely SOTA strings to see which ones are available
        sota_candidates = [
            "gemini-3.1-pro-preview",
            "gemini-3.1-pro",
            "gemini-2.0-flash-001",
            "gemini-2.0-flash-lite-001",
            "gemini-1.5-pro-002",
            "gemini-1.5-flash-002"
        ]
        
        available = []
        for model_id in sota_candidates:
            print(f"🛰️ Testing Pulse: {model_id}...", end=" ", flush=True)
            try:
                model = GenerativeModel(model_id)
                response = model.generate_content("Ping.", generation_config={"max_output_tokens": 5})
                if response.text:
                    print("✅ ONLINE")
                    available.append(model_id)
            except Exception as e:
                # Truncate error message for cleaner output
                err_msg = str(e).split('\n')[0][:50]
                print(f"❌ OFFLINE ({err_msg})")
        
        print("\n--- 💎 DEFINITIVE BEST AVAILABLE ---\n")
        if available:
            # First one in sota_candidates that is online is the 'best'
            for a in available:
                print(f"🏆 {a}")
                # We can stop here or show all
        else:
            print("❌ No SOTA candidates executing in this region.")

    except ImportError:
        print("❌ Vertex AI SDK not found. Install google-cloud-aiplatform.")
    except Exception as e:
        print(f"❌ Discovery Fault: {e}")

if __name__ == "__main__":
    discover_models()