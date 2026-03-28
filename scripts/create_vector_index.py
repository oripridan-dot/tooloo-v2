# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining create_vector_index.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.405256
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import os
from google.cloud import firestore_admin_v1

def create_vector_index():
    project_id = os.getenv("GCP_PROJECT_ID", "too-loo-zi8g7e")
    client = firestore_admin_v1.FirestoreAdminClient()
    
    # Target the generic "(default)" database and the "psyche_ground_truth" collection group
    parent = f"projects/{project_id}/databases/(default)/collectionGroups/psyche_ground_truth"
    
    # Define the 768-dimensional Flat index for the 'embedding' vector field
    index = firestore_admin_v1.Index(
        query_scope=firestore_admin_v1.Index.QueryScope.COLLECTION,
        fields=[
            firestore_admin_v1.Index.IndexField(
                field_path="embedding",
                vector_config=firestore_admin_v1.Index.IndexField.VectorConfig(
                    dimension=768,
                    flat=firestore_admin_v1.Index.IndexField.VectorConfig.FlatIndex()
                )
            )
        ]
    )
    
    print(f"Provisioning Firestore Vector Index on {parent}...")
    try:
        operation = client.create_index(request={"parent": parent, "index": index})
        print("Index creation initiated. This operation happens in the GCP background.")
        print("You can track its status in the Firebase/Firestore console.")
    except Exception as e:
        if "already exists" in str(e).lower() or "already being created" in str(e).lower():
            print("Index is already created or currently building.")
        else:
            print(f"Error creating index: {e}")

if __name__ == "__main__":
    create_vector_index()
