#!/workspaces/tooloo-v2/.venv/bin/python
"""trigger_cloud_crucible.py

Submits a serverless 5-cycle self-improvement crucible run to Google Cloud Build.
Sources code directly from the GitHub repository — no GCS bucket required.

Usage:
    python trigger_cloud_crucible.py
    python trigger_cloud_crucible.py --async   # fire-and-forget (don't wait)
    python trigger_cloud_crucible.py --cycles 3
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from google.cloud.devtools import cloudbuild_v1
from google.oauth2 import service_account

# ── constants ──────────────────────────────────────────────────────────────────
GITHUB_OWNER  = "oripridan-dot"
GITHUB_REPO   = "tooloo-v2"
GITHUB_BRANCH = "main"
DEFAULT_CYCLES = 5
MACHINE_TYPE   = cloudbuild_v1.BuildOptions.MachineType.E2_HIGHCPU_8

# Repo name as registered in Cloud Build GitHub app connection.
# Format: github_{owner}_{repo}  (underscores replace hyphens)
_CLOUD_BUILD_REPO_NAME = f"github_{GITHUB_OWNER.replace('-','_')}_{GITHUB_REPO.replace('-','_')}"


def _load_credentials(key_path: str):
    if not os.path.exists(key_path):
        print(f"[!] Service Account key not found: {key_path}")
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return creds


def submit_serverless_crucible(cycles: int = DEFAULT_CYCLES, wait: bool = True) -> None:
    print("[*] TooLoo V2 — Serverless Crucible Trigger")
    print(f"    Source : github.com/{GITHUB_OWNER}/{GITHUB_REPO}@{GITHUB_BRANCH}")
    print(f"    Cycles : {cycles}")
    print(f"    Machine: E2_HIGHCPU_8")
    print()

    key_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "too-loo-zi8g7e-9fdca526cf9a.json")
    creds = _load_credentials(key_path)
    project_id = creds.project_id
    print(f"[*] Authenticated as: {creds.service_account_email}")
    print(f"[*] Project         : {project_id}")

    client = cloudbuild_v1.CloudBuildClient(credentials=creds)

    # ── Build definition ────────────────────────────────────────────────────────
    # Source comes directly from GitHub — zero GCS bucket permission needed.
    build = cloudbuild_v1.Build(
        source=cloudbuild_v1.Source(
            repo_source=cloudbuild_v1.RepoSource(
                project_id=project_id,
                repo_name=_CLOUD_BUILD_REPO_NAME,
                branch_name=GITHUB_BRANCH,
            )
        ),
        steps=[
            cloudbuild_v1.BuildStep(
                name="python:3.11-slim",
                entrypoint="bash",
                args=[
                    "-c",
                    (
                        "pip install --quiet -r requirements.txt && "
                        "pip install --quiet -e . && "
                        f"TOOLOO_LIVE_TESTS=1 python run_cycles.py --cycles {cycles}"
                    ),
                ],
                env=["TOOLOO_LIVE_TESTS=1"],
            )
        ],
        options=cloudbuild_v1.BuildOptions(
            machine_type=MACHINE_TYPE,
            logging=cloudbuild_v1.BuildOptions.LoggingMode.CLOUD_LOGGING_ONLY,
        ),
        timeout="3600s",
    )

    print("\n[*] Submitting build to Cloud Build ...")
    try:
        operation = client.create_build(project_id=project_id, build=build)
        build_meta = operation.metadata
        build_id = build_meta.build.id if build_meta else "(pending)"
        print(f"[+] Build queued — ID: {build_id}")
        console_url = (
            f"https://console.cloud.google.com/cloud-build/builds/{build_id}"
            f"?project={project_id}"
        )
        print(f"[+] Live logs  : {console_url}")

        if wait:
            print("\n[*] Waiting for remote execution (this may take 5-10 min) ...")
            t0 = time.time()
            result = operation.result()          # blocks until complete
            elapsed = int(time.time() - t0)
            status_name = cloudbuild_v1.Build.Status(result.status).name
            if result.status == cloudbuild_v1.Build.Status.SUCCESS:
                print(f"\n[+] CRUCIBLE COMPLETE in {elapsed}s — Status: {status_name}")
                print(f"[+] Logs: {result.log_url}")
            else:
                print(f"\n[!] Build ended with status: {status_name} after {elapsed}s")
                print(f"[!] Logs: {result.log_url}")
        else:
            print("[*] Async mode — build running in the cloud. Check logs at the URL above.")

    except Exception as exc:
        print(f"\n[!] Submission failed: {exc}")
        _diagnose(exc)


def _diagnose(exc: Exception) -> None:
    msg = str(exc)
    if "bucket" in msg.lower() or "storage" in msg.lower():
        print("\n>>> FIX: Add 'Storage Object Admin' to the Service Account in GCP IAM.")
    elif "403" in msg or "forbidden" in msg.lower() or "permission" in msg.lower():
        print("\n>>> FIX: Ensure the SA has 'Cloud Build Editor' + 'Service Account User' roles.")
    elif "repo" in msg.lower() or "github" in msg.lower():
        print("\n>>> FIX: Connect your GitHub repo to Cloud Build at:")
        print(f"    https://console.cloud.google.com/cloud-build/triggers/connect")
    else:
        print("\n>>> Check Cloud Build logs in the GCP Console for details.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TooLoo V2 Cloud Crucible Trigger")
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--async", dest="async_mode", action="store_true")
    args = parser.parse_args()
    submit_serverless_crucible(cycles=args.cycles, wait=not args.async_mode)
