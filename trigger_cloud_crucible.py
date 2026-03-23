import os
import json
import uuid
from google.cloud.devtools import cloudbuild_v1
from google.oauth2 import service_account

def submit_serverless_crucible():
    print("[*] Initialising Serverless GCP Crucible Execution Pipeline...")
    
    # Load Credentials
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "too-loo-zi8g7e-9fdca526cf9a.json")
    if not os.path.exists(creds_path):
        print(f"[!] Critical Error: Could not locate Service Account at {creds_path}")
        return
        
    creds = service_account.Credentials.from_service_account_file(creds_path)
    project_id = creds.project_id
    
    client = cloudbuild_v1.CloudBuildClient(credentials=creds)
    build = cloudbuild_v1.Build()
    
    # We define the build steps to clone, setup, and run 5 cycles
    build.steps = [
        {
            "name": "python:3.10-slim",
            "entrypoint": "bash",
            "args": [
                "-c",
                "pip install -r requirements.txt && pip install -e . && pytest tests/ && TOOLOO_LIVE_TESTS=1 python run_cycles.py --cycles 5"
            ],
            "env": [
                "TOOLOO_LIVE_TESTS=1"
                # Note: The GCP JSON key needs to be bound via Secret Manager in production
            ]
        }
    ]
    
    build.options = {"machine_type": "E2_HIGHCPU_8"}
    
    print(f"[*] Submitting the full 5-Wave Crucible to Google Cloud Build (Serverless Execution) for Project: {project_id}...")
    try:
        operation = client.create_build(project_id=project_id, build=build)
        print(f"[*] Successfully queued Build ID. Waiting for async execution...")
        result = operation.result()
        print(f"[*] Remote Crucible Execution Complete! Status: {result.status}")
    except Exception as e:
        print(f"[!] Warning: Could not submit build (API might be disabled or missing billing on project). Reason: {e}")
        print("\n---> ACTION REQUIRED: Please go to GCP IAM Console and grant 'Cloud Build Editor' and 'Service Account User' to your service account.")

if __name__ == "__main__":
    submit_serverless_crucible()
