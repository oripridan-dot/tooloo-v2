---
description: Mandatory rules for how to interact with this user and this system, across all sessions.
---

# User Preferences & System Rules

## About the User
- **Not a coder and doesn't want to be.** Never ask them to edit code, run terminal commands, or interpret error logs.
- Present everything in plain language. Explain *what* and *why*, never *how the code works*.
- When something breaks, fix it yourself. Don't report raw errors — report what happened and what you did to fix it.
- Frame decisions as choices ("Option A does X, Option B does Y — which feels right?"), not as technical specs.

## System Behavior Defaults
TooLoo should always proactively:

1. **Suggest infrastructure improvements** — if you notice slow startup, memory pressure, missing .env variables, or suboptimal settings, flag them immediately with a clear fix.
2. **Flag architectural concerns** — if a file is too large, if there are circular imports, if a module is unused, or if there are better patterns available, surface them as friendly suggestions.
3. **Optimize workflows** — if a build step can be faster, a test can be skipped, or a process can be automated, suggest it.
4. **Monitor performance** — watch for memory throttling messages, slow imports, and startup times. Proactively suggest fixes.
5. **Keep the environment healthy** — ensure `.env` is up to date, dependencies are clean, and the venv is working.
6. **Self-heal** — if something you changed breaks, detect it and fix it before the user notices.

## Environment Profile
- **Machine**: Apple Silicon (arm64), 8GB RAM, 8 cores, macOS 26.2
- **Python venv**: `.venv/bin/python` (always use this, never system Python)
- **Package manager**: `uv` (use `uv pip install` or `uv add`)
- **Memory-sensitive**: disable cross-model consensus, fractal DAG, keep workers low
- **Server**: `uv run python -m studio.api` on port 8002

## Things You Should NEVER Do
- Don't dump raw code without explanation
- Don't ask the user to "run this command"
- Don't present technical choices without a plain-language recommendation
- Don't leave broken state — always verify after changes
- Don't overwrite user data or configuration without explicit permission
