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

PROJECT_ID     = "too-loo-zi8g7e"
GCS_BUCKET     = f"{PROJECT_ID}_cloudbuild"
DEFAULT_CYCLES = 5
MACHINE_TYPE   = cloudbuild_v1.BuildOptions.MachineType.E2_HIGHCPU_8
SA_KEY_PATH    = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "too-loo-zi8g7e-9fdca526cf9a.json")

SKIP_PATTERNS = {
    ".venv", "__pycache__", ".git", ".pytest_cache", ".mypy_cache",
    "google-cloud-sdk", "node_modules", ".hypothesis", "tooloo_v2.egg-info",
    "too-loo-zi8g7e-9fdca526cf9a.json",
}

def _load_credentials():
    if not Path(SA_KEY_PATH).exists():
        print(f"[!] SA key not found: {SA_KEY_PATH}")
        sys.exit(1)
    return service_account.Credentials.from_service_account_file(
        SA_KEY_PATH, scopes=["https://www.googleapis.com/auth/cloud-platform"])

def _zip_workspace() -> bytes:
    print("[*] Zipping workspace...")
    buf = io.BytesIO()
    root = Path(".")
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if set(path.parts) & SKIP_PATTERNS:
                continue
            if path.is_file():
                zf.write(path)
    size_mb = buf.tell() / 1_048_576
    print(f"    Zip size: {size_mb:.1f} MB")
    buf.seek(0)
    return buf.read()

def _upload_to_gcs(zip_bytes: bytes, creds) -> str:
    object_name = f"source/tooloo-crucible-{int(time.time())}.zip"
    print(f"[*] Uploading to gs://{GCS_BUCKET}/{object_name} ...")
    client = gcs.Client(project=PROJECT_ID, credentials=creds)
    blob = client.bucket(GCS_BUCKET).blob(object_name)
    blob.upload_from_string(zip_bytes, content_type="application/zip")
    print("    [+] Upload complete.")
    return object_name

def submit_serverless_crucible(cycles: int = DEFAULT_CYCLES, wait: bool = True) -> None:
    print("=" * 60)
    print("  TooLoo V2 — Serverless Crucible (GCS zip upload)")
    print(f"  Cycles: {cycles}  |  Machine: E2_HIGHCPU_8")
    print("=" * 60)
    creds = _load_credentials()
    print(f"[*] Auth: {creds.service_account_email}")
    zip_bytes = _zip_workspace()
    object_name = _upload_to_gcs(zip_bytes, creds)
    client = cloudbuild_v1.CloudBuildClient(credentials=creds)
    build = cloudbuild_v1.Build(
        source=cloudbuild_v1.Source(
            storage_source=cloudbuild_v1.StorageSource(bucket=GCS_BUCKET, object_=object_name)
        ),
        steps=[cloudbuild_v1.BuildStep(
            name="python:3.12-slim",
            entrypoint="bash",
            args=["-c",
                "set -e && "
                "apt-get update -qq && apt-get install -y -qq git build-essential && "
                "pip install --quiet --upgrade pip setuptools wheel && "
                "pip install --quiet -e '.[dev]' && "
                f"TOOLOO_LIVE_TESTS=1 python run_cycles.py --cycles {cycles} && "
                "echo '[+] Crucible complete.'"
            ],
            env=["TOOLOO_LIVE_TESTS=1"],
        )],
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
            print("\n[*] Waiting for remote execution (5-15 min)...")
            t0 = time.time()
            result = operation.result()
            elapsed = int(time.time() - t0)
            status = cloudbuild_v1.Build.Status(result.status).name
            if result.status == cloudbuild_v1.Build.Status.SUCCESS:
                print(f"\n[+] CRUCIBLE COMPLETE in {elapsed}s — Status: {status}")
            else:
                print(f"\n[!] Build ended: {status} after {elapsed}s")
            print(f"    Logs: {result.log_url}")
        else:
            print("[*] Async — build running in cloud. Check URL above.")
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
