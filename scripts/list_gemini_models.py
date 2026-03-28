# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining list_gemini_models.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.393219
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

from engine.config import gemini_client

if not gemini_client:
    print("Gemini API client not configured")
else:
    try:
        models = gemini_client.models.list()
        for m in models:
            # name usually starts with 'models/'
            print(f"{m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")
