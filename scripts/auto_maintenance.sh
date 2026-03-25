#!/usr/bin/env bash
# scripts/auto_maintenance.sh
# 
# Autonomous Maintenance Sequence for TooLoo V2
# This script is designed to be triggered autonomously by the TooLoo engine
# (via the MCP run_command tool) when it evaluates that the system state is stable
# and requires consolidation, cleanup, and version control sync.

set -e

echo "============================================================"
echo " 🧹 Initiating TooLoo Autonomous Maintenance Sequence"
echo " Time: $(date)"
echo "============================================================"

# 1. Cleanup Temporary files
echo "  [1/3] Deep cleaning pycache and temporary buffers..."
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type f -name "*.pyd" -delete
find . -type d -name ".pytest_cache" -exec rm -rf {} +
find . -type d -name ".mypy_cache" -exec rm -rf {} +
find . -type d -name ".pyre" -exec rm -rf {} +
echo "  [1/3] ✅ Cleanup complete."

# 2. Status check
echo "  [2/3] Checking system status and Git tree..."
git status -s

# 3. Commit and Push
echo "  [3/3] Synchronizing Version Control (Git)..."
git add .
git commit -m "chore(auto-maintain): Autonomous system maintenance, doc updates, and cleanup sequence triggered by TooLoo engine." || echo "  -> No changes to commit."

# Attempt push, if it fails due to remote configuration, we notify but don't break.
if git push origin main; then
    echo "  [3/3] ✅ Git push successful to 'main'."
else
    echo "  [3/3] ⚠️ Git push failed or remote 'origin/main' not configured properly. Changes committed locally."
fi

echo "============================================================"
echo " ✅ Autonomous Maintenance Sequence Complete."
echo "============================================================"
