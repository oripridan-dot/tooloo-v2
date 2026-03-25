---
description: How to build features for the TooLoo AI Design Studio — grounded, real, iterative.
---

# Build and Verify Workflow

## Ground Rules
- The **user is NOT a coder** and does not want to be. Never dump raw code or expect them to edit files manually.
- Always explain what you're doing in plain language first. If there's a decision to make, present options clearly with pros/cons.
- When you make changes, verify them yourself before telling the user anything worked.
- If something breaks, fix it — don't just report the error.

## Step 1: Understand the Request
- Restate what the user wants in your own words (one sentence).
- Ask clarifying questions only if truly ambiguous.

## Step 2: Plan
- Create or update `implementation_plan.md` with a plain-language summary.
- List what files will change and why (user-friendly, no code dumps).

## Step 3: Build
// turbo-all
- Make the code changes.
- After each significant change, run the import check:
```
cd /Users/oripridan/ANTIGRAVITY/tooloo-v2 && .venv/bin/python -c "from studio.api import app; print('OK')"
```

## Step 4: Verify
// turbo-all
- Run the relevant tests:
```
cd /Users/oripridan/ANTIGRAVITY/tooloo-v2 && .venv/bin/python -m pytest tests/ -x -q --timeout=30 2>&1 | tail -20
```
- If the server is running, test affected endpoints in the browser.

## Step 5: Report
- Tell the user what changed in plain language.
- If there are UI changes, show a screenshot.
- If there are performance impacts, explain in terms of "faster/slower" and "uses more/less memory".

## Environment Notes (8GB Apple Silicon Mac)
- Always use `.venv/bin/python` — not system Python.
- Package manager is `uv` — use `uv pip install` or `uv add` for dependencies.
- Max worker counts should stay ≤ 4 (EXECUTOR_MAX_WORKERS) and ≤ 8 (SANDBOX_MAX_WORKERS).
- Watch for memory throttling messages ("Moderate memory usage... Throttling strokes").
- Cross-model consensus is OFF to save RAM.
- Fractal DAG expansion is OFF to save RAM.
