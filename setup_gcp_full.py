#!/workspaces/tooloo-v2/.venv/bin/python
"""setup_gcp_full.py — One-shot GCP + GitHub full migration setup.

What this script does
---------------------
1. Grants all required IAM roles to the TooLoo Service Account.
2. Uploads the SA JSON as `GCP_CREDENTIALS` to the GitHub repository
   secrets (using the GitHub REST API + Libsodium encryption).
3. Prints a direct link to trigger the GitHub Actions crucible workflow.

Prerequisites
-------------
  - GITHUB_TOKEN env var OR ~/.config/gh/hosts.yml (gh CLI login)
  - too-loo-zi8g7e-9fdca526cf9a.json present in the workspace root
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import requests

# ── config ────────────────────────────────────────────────────────────────────
SA_KEY_PATH   = "too-loo-zi8g7e-9fdca526cf9a.json"
PROJECT_ID    = "too-loo-zi8g7e"
GH_OWNER      = "oripridan-dot"
GH_REPO       = "tooloo-v2"
GH_SECRET_NAME = "GCP_CREDENTIALS"

# Roles the service account needs for full cloud operation
REQUIRED_ROLES = [
    "roles/cloudbuild.builds.builder",   # submit + manage builds
    "roles/iam.serviceAccountUser",       # run as SA
    "roles/storage.objectAdmin",          # GCS bucket for build source
    "roles/logging.logWriter",            # write build logs
    "roles/run.invoker",                  # invoke Cloud Run services
    "roles/artifactregistry.reader",      # pull container images
    "roles/aiplatform.user",              # Vertex AI inference
    "roles/secretmanager.secretAccessor", # read secrets
    "roles/datastore.user",               # Firestore for Cold Memory
]

# ── helpers ───────────────────────────────────────────────────────────────────

def _load_sa_key() -> dict:
    p = Path(SA_KEY_PATH)
    if not p.exists():
        print(f"[!] Cannot find SA key at: {SA_KEY_PATH}")
        sys.exit(1)
    return json.loads(p.read_text())


def _github_token() -> str:
    """Return GitHub token from env, gh CLI config, or prompt."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token
    # Try gh CLI stored credentials
    gh_hosts = Path.home() / ".config" / "gh" / "hosts.yml"
    if gh_hosts.exists():
        for line in gh_hosts.read_text().splitlines():
            line = line.strip()
            if line.startswith("oauth_token:"):
                token = line.split(":", 1)[1].strip()
                if token:
                    return token
    print("[!] No GITHUB_TOKEN found. Set it with:")
    print("      export GITHUB_TOKEN=<your_token>")
    print("    Or log in with: gh auth login")
    sys.exit(1)


def grant_iam_roles(sa_email: str, key_data: dict) -> None:
    """Grant all required roles using google-cloud-resource-manager."""
    print("\n[1/3] Granting IAM roles to Service Account...")
    try:
        from google.cloud import resourcemanager_v3
        from google.iam.v1 import iam_policy_pb2, policy_pb2
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_info(
            key_data,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        client = resourcemanager_v3.ProjectsClient(credentials=creds)
        resource = f"projects/{PROJECT_ID}"

        # Get current policy
        policy = client.get_iam_policy(request={"resource": resource})
        member = f"serviceAccount:{sa_email}"
        modified = False

        for role in REQUIRED_ROLES:
            binding_found = False
            for binding in policy.bindings:
                if binding.role == role:
                    binding_found = True
                    if member not in binding.members:
                        binding.members.append(member)
                        modified = True
                        print(f"    + Added {role}")
                    else:
                        print(f"    ✓ Already has {role}")
                    break
            if not binding_found:
                policy.bindings.add(role=role, members=[member])
                modified = True
                print(f"    + Granted {role}")

        if modified:
            client.set_iam_policy(request={"resource": resource, "policy": policy})
            print("    [+] IAM policy updated successfully.")
        else:
            print("    [+] All roles already in place. No changes needed.")

    except Exception as e:
        print(f"    [!] IAM grant failed: {e}")
        print("    --> Continuing anyway; roles may already exist.")


def push_github_secret(sa_key_json: str, token: str) -> None:
    """Encrypt and upload SA JSON as GitHub Actions secret."""
    print(f"\n[2/3] Uploading {GH_SECRET_NAME} to GitHub Actions secrets...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Get repo public key for secret encryption
    pk_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/secrets/public-key"
    resp = requests.get(pk_url, headers=headers, timeout=15)
    if resp.status_code != 200:
        print(f"    [!] Could not fetch repo public key: {resp.status_code} {resp.text}")
        return

    pk_data  = resp.json()
    key_id   = pk_data["key_id"]
    pub_key  = pk_data["key"]

    # Encrypt with libsodium (PyNaCl)
    from nacl import encoding, public as nacl_public
    public_key = nacl_public.PublicKey(pub_key.encode(), encoding.Base64Encoder)
    sealed = nacl_public.SealedBox(public_key)
    encrypted = sealed.encrypt(sa_key_json.encode())
    encrypted_b64 = base64.b64encode(encrypted).decode()

    # Upload secret
    secret_url = f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/actions/secrets/{GH_SECRET_NAME}"
    payload = {"encrypted_value": encrypted_b64, "key_id": key_id}
    put_resp = requests.put(secret_url, headers=headers, json=payload, timeout=15)

    if put_resp.status_code in (201, 204):
        print(f"    [+] Secret '{GH_SECRET_NAME}' uploaded successfully.")
    else:
        print(f"    [!] Secret upload failed: {put_resp.status_code} {put_resp.text}")


def trigger_workflow(token: str) -> None:
    """Fire a workflow_dispatch event on the crucible workflow."""
    print("\n[3/3] Triggering crucible workflow on GitHub Actions...")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    dispatch_url = (
        f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}"
        f"/actions/workflows/gcp-crucible.yaml/dispatches"
    )
    payload = {"ref": "main", "inputs": {"cycles": "5"}}
    resp = requests.post(dispatch_url, headers=headers, json=payload, timeout=15)

    if resp.status_code == 204:
        print("    [+] Workflow dispatched! Live logs at:")
        print(f"    https://github.com/{GH_OWNER}/{GH_REPO}/actions")
    else:
        print(f"    [!] Dispatch failed: {resp.status_code} {resp.text}")
        print(f"\n    Manual trigger URL:")
        print(f"    https://github.com/{GH_OWNER}/{GH_REPO}/actions/workflows/gcp-crucible.yaml")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  TooLoo V2 — Full GCP Migration & GitHub Actions Setup")
    print("=" * 60)

    key_data = _load_sa_key()
    sa_email = key_data["client_email"]
    sa_key_json = json.dumps(key_data)

    print(f"\n  Service Account : {sa_email}")
    print(f"  GCP Project     : {PROJECT_ID}")
    print(f"  GitHub Repo     : {GH_OWNER}/{GH_REPO}")

    grant_iam_roles(sa_email, key_data)

    token = _github_token()
    push_github_secret(sa_key_json, token)
    trigger_workflow(token)

    print("\n" + "=" * 60)
    print("  Setup complete! ")
    print("  Monitor the crucible run at:")
    print(f"  https://github.com/{GH_OWNER}/{GH_REPO}/actions")
    print("=" * 60)


if __name__ == "__main__":
    main()
