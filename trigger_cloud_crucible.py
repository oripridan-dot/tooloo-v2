#!/workspaces/tooloo-v2/.venv/bin/python
"""trigger_cloud_crucible.py

Submits a serverless 5-cycle self-improvement crucible run to Google Cloud Build.
Zips the local workspace, uploads to GCS, then submits — no GitHub connection needed.

Usage:
    python trigger_cloud_crucible.py
    python trigger_cloud_crucible.py --async   # fire-and-forget
    python trigger_cloud_crucible.py --cycles 3
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
import zipfile
from pathlib import Path

from google.cloud import storage as gcs
from google.cloud.devtools import cloudbuild_v1
from google.oauth2 import service_account

# ── constants ──────────────────────────────────────────────────────────────────
PROJECT_ID     = "too-loo-zi8g7e"
GCS_BUCKET     = f"{PROJECT_ID}_cloudbuild"
DEFAULT_CYCLES = 5
MACHINE_TYPE   = cloudbuild_v1.BuildOptions.MachineType.E2_HIGHCPU_8
SA_KEY_PATH    = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS",
                                "too-loo-zi8g7e-9fdca526cf9a.json")

# Files/dirs to skip when zipping the workspace
SKIP_PATTERNS = {
    ".venv", "__pycache__", ".git", ".pytest_cache", ".mypy_cache",
    "google-cloud-sdk", "google-cloud-cli-linux-x86_64.tar.gz",
    "node_modules", ".hypothesis", "tooloo_v2.egg-info",
    "too-loo-zi8g7e-9fdca526cf9a.json",   # never upload the SA key
}


def _load_credentials():
    if not Path(SA_KEY_PATH).exists():
        print(f"[!] SA key not found: {SA_KEY_PATH}")
        sys.exit(1)
    return service_account.Credentials.from_service_account_file(
        SA_KEY_PATH,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


def _zip_workspace() -> bytes:
    """Zip the current workspace into an in-memory bytes object."""
    print("[*] Zipping workspace (skipping .venv, .git, caches)...")
    buf = io.BytesIO()
    root = Path(".")
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            # Skip if any ancestor matches a skip pattern
            parts = set(path.parts)
            if parts & SKIP_PATTERNS:
                continue
            if path.is_file():
                zf.write(path)
    size_mb = buf.tell() / 1_048_576
    print(f"    Zip size: {size_mb:.1f} MB")
    buf.seek(0)
    return buf.read()


def _upload_to_gcs(zip_bytes: bytes, creds) -> str:
    """Upload zip to GCS and return the object name."""
    object_name = f"source/tooloo-crucible-{int(time.time())}.zip"
    print(f"[*] Uploading source to gs://{GCS_BUCKET}/{object_name} ...")
    client = gcs.Client(project=PROJECT_ID, credentials=creds)
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(object_name)
    blob.upload_from_string(zip_bytes, content_type="application/zip")
    print(f"    [+] Upload complete.")
    return object_name


def submit_serverless_crucible(cycles: int = DEFAULT_CYCLES, wait: bool = True) -> None:
    print("=" * 60)
    print("  TooLoo V2 — Serverless Crucible (GCS source upload)")
    print(f"  Cycles : {cycles}  |  Machine: E2_HIGHCPU_8")
    print("=" * 60)

    creds = _load_credentials()
    print(f"[*] Auth: {creds.service_account_email}")

    # 1. Zip and upload
    zip_bytes = _zip_workspace()
    object_name = _upload_to_gcs(zip_bytes, creds)

    # 2. Submit build pointing at the GCS object
    client = cloudbuild_v1.CloudBuildClient(credentials=creds)
    build = cloudbuild_v1.Build(
        source=cloudbuild_v1.Source(
            storage_source=cloudbuild_v1.StorageSource(
                bucket=GCS_BUCKET,
                object_=object_name,
            )
        ),
        steps=[
            cloudbuild_v1.BuildStep(
                name="python:3.12-slim",
                entrypoint="bash",
                args=[
                    "-c",
                    (
                        "set -e && "
                        "apt-get update -qq && apt-get install -y -qq git build-essential && "
                        "pip install --quiet --upgrade pip setuptools wheel && "
                        f"pip install --quiet -e '.[dev]' && "
                        f"TOOLOO_LIVE_TESTS=1 python run_cycles.py --cycles {cycles} && "
                        "echo '[+] Crucible complete.'"
                    ),
                ],
                env=["TOOLOO_LIVE_TESTS=1"],
            )
        ],
        options=cloudbuild_v1.BuildOptions(
            machine_type=MACHINE_TYPE,
            logging=cloudbuild_v1.BuildOptions.LoggingMode.GCS_ONLY,
        ),
        timeout="3600s",
    )

    print("\n[*] Submitting build to Cloud Build...")
    try:
        operation = client.create_build(project_id=PROJECT_ID, build=build)
        meta = operation.metadata
        build_id = meta.build.id if meta else "(pending)"
        print(f"[+] Build queued — ID: {build_id}")
        print(f"[+] Live logs: https://console.cloud.google.com/cloud-build/builds/{build_id}?project={PROJECT_ID}")

        if wait:
            print("\n[*] Waiting for remote execution (5-10 min)...")
            t0 = time.time()
            result = operation.result()
            elapsed = int(time.time() - t0)
            status = cloudbuild_v1.Build.Status(result.status).name
            if result.status == cloudbuild_v1.Build.Status.SUCCESS:
                print(f"\n[+] CRUCIBLE COMPLETE in {elapsed}s — Status: {status}")
                print(f"[+] Logs: {result.log_url}")
            else:
                print(f"\n[!] Build ended: {status} after {elapsed}s")
                print(f"[!] Logs: {result.log_url}")
        else:
            print("[*] Async mode — build running in cloud. Check URL above.")

    except Exception as exc:
        print(f"\n[!] Submission failed: {exc}")
        msg = str(exc).lower()
        if "bucket" in msg or "storage" in msg:
            print(">>> FIX: Add 'Storage Admin' role to the SA in GCP IAM.")
        elif "403" in msg or "permission" in msg:
            print(">>> FIX: SA needs 'Cloud Build Editor' + 'Service Account User'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--async", dest="async_mode", action="store_true")
    args = parser.parse_args()
    submit_serverless_crucible(cycles=args.cycles, wait=not args.async_mode)

from __future__ import annotations

import argparse
import os
import sys
import time
from google.cloud.devtools import cloudbuild_v1
from google.oauth2 import service_account

# ── constants ──────────────────────────────────────────────────────────────────
GITHUB_OWNER = "oripridan-dot"
GITHUB_REPO = "tooloo-v2"
GITHUB_BRANCH = "main"
DEFAULT_CYCLES = 5
MACHINE_TYPE = cloudbuild_v1.BuildOptions.MachineType.E2_HIGHCPU_8

# Repo name as registered in Cloud Build GitHub app connection.
# Format: github_{owner}_{repo}  (underscores replace hyphens)
_CLOUD_BUILD_REPO_NAME = f"github_{GITHUB_OWNER.replace('-', '_')}_{GITHUB_REPO.replace('-', '_')}"


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
    print(
        f"    Source : github.com/{GITHUB_OWNER}/{GITHUB_REPO}@{GITHUB_BRANCH}")
    print(f"    Cycles : {cycles}")
    print(f"    Machine: E2_HIGHCPU_8")
    print()

    key_path = os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS", "too-loo-zi8g7e-9fdca526cf9a.json")
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
                print(
                    f"\n[+] CRUCIBLE COMPLETE in {elapsed}s — Status: {status_name}")
                print(f"[+] Logs: {result.log_url}")
            else:
                print(
                    f"\n[!] Build ended with status: {status_name} after {elapsed}s")
                print(f"[!] Logs: {result.log_url}")
        else:
            print(
                "[*] Async mode — build running in the cloud. Check logs at the URL above.")

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
    parser = argparse.ArgumentParser(
        description="TooLoo V2 Cloud Crucible Trigger")
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--async", dest="async_mode", action="store_true")
    args = parser.parse_args()
    submit_serverless_crucible(cycles=args.cycles, wait=not args.async_mode)
