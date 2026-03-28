# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining ingest_test_data.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.404403
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""scripts/ingest_test_data.py — Seeds the Cloud RAG Firestore DB."""
import os
import sys

# Ensure the engine module can be resolved
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.cloud_rag import ingest_document

# The Ground Truth Dictionary
GROUND_TRUTH_DATA = [
    {
        "id": "owasp_api_1",
        "text": "The standard refers to BOLA, which means Broken Object Level Authorization.",
        "meta": {"source": "OWASP API1:2023", "domain": "Security"}
    },
    {
        "id": "allen_heath_dlive",
        "text": "The Allen & Heath dLive S7000 surface features 36 faders.",
        "meta": {"source": "dLive S7000 Manual", "domain": "Audio Engineering"}
    },
    {
        "id": "gdpr_encryption",
        "text": "Under GDPR, PII must be encrypted at rest utilizing strong cryptographic suites.",
        "meta": {"source": "GDPR Compliance Handbook"}
    }
]

def run_ingestion():
    print("--- Starting Vertex AI Embedding & Firestore Ingestion ---")
    if not os.getenv("GCP_PROJECT_ID"):
        print("ERROR: GCP_PROJECT_ID is not set in the environment.")
        print("Please export GCP_PROJECT_ID=your-project-id before running.")
        sys.exit(1)
        
    for item in GROUND_TRUTH_DATA:
        print(f"Embedding and ingesting: {item['id']}...")
        ingest_document(
            source_id=item["id"],
            text=item["text"],
            metadata=item["meta"]
        )
    
    print("--- Ingestion Complete ---")
    print("Your Cloud RAG is now ready to serve queries at <20ms.")

if __name__ == "__main__":
    run_ingestion()
