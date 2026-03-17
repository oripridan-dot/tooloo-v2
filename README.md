# TooLoo V2 — Pure DAG Cognitive OS

> **Seed repository.** TooLoo builds itself from this minimal foundation.

## Architecture

```
Mandate text
  → MandateRouter      (intent classification + circuit breaker)
  → Tribunal           (OWASP poison detection → heal → PsycheBank capture)
  → TopologicalSorter  (DAG wave planning — cycle-rejecting)
  → JITExecutor        (parallel fan-out via ThreadPoolExecutor)
  → Governor Dashboard (FastAPI + SSE live events)
```

## Laws in Force

| Law | Rule |
|-----|------|
| 6   | Version pinned at `0.1.0` — only TooLoo bumps versions |
| 9   | All credentials from `.env` — never hardcoded |
| 14  | Circuit breaker at 0.85 confidence threshold |
| 17  | Stateless processors — no shared mutable state |
| 19  | Epistemic humility — confidence gate before every action |
| 20  | Consent gate at every phase transition |

## Quickstart

```bash
cp .env.example .env
# fill in GEMINI_API_KEY and GITHUB_TOKEN

pip install -e ".[dev]"
tooloo-v2                    # start Governor Dashboard on :8002
```

## Tests

```bash
pytest tests/ -v             # all offline, < 100ms
```

## Structure

```
engine/
  config.py        — single source of truth for all env vars
  graph.py         — CognitiveGraph + TopologicalSorter + CausalProvenanceTracker
  router.py        — MandateRouter + circuit breaker
  tribunal.py      — OWASP tribunal + heal + PsycheBank capture
  psyche_bank.py   — .cog.json rule store
  executor.py      — JIT fan-out (threading)
studio/
  api.py           — FastAPI Governor Dashboard
  static/
    index.html     — dark professional UI
psyche_bank/
  forbidden_patterns.cog.json  — 5 pre-seeded OWASP rules
tests/
  test_v2.py       — proof harness (3 dimensions, all offline)
```
