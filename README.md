# TooLoo V2 — Pure DAG Cognitive OS

**Version 2.2** · `feature/autonomous-agentic-mcp`

TooLoo V2 is a self-building autonomous intelligence engine with full agentic capabilities via the Model Context Protocol (MCP). Every request flows
through a deterministic Directed Acyclic Graph (DAG) of cognitive processes — scoped, executed, rigorously audited by an internal Tribunal, and refined without human intervention. The system monitors its own code, generates improvement prescriptions, and executes them via secure sandboxed tools.

---

## Architecture

```
Mandate (natural language)
       │
       ▼
 MandateRouter ─── circuit breaker (0.85) ─── JITBooster (SOTA signals)
       │
       ▼
 NStrokeEngine   ←─ MetaArchitect (dynamic DAG topology)
       │                 │
  Wave 1 ─ Wave 2 ─ ... Wave N   (topological order, parallel within wave)
       │
       ▼
  JITExecutor (ThreadPoolExecutor fan-out, stateless nodes)
       │
       ▼
  Tribunal (OWASP poison scan on every artefact)
       │
       ▼
  RefinementLoop → RefinementSupervisor (autonomous healing on 3 failures)
```

### Engine Components (17 · 6 waves)

| Wave | Component | Role |
|------|-----------|------|
| 1 | `config` | Single source of truth — loads from `.env` |
| 1 | `psyche_bank` | Thread-safe `.cog.json` rule store |
| 2 | `graph` | CognitiveGraph — DAG acyclicity enforcement |
| 2 | `tribunal` | OWASP poison scanner (12 patterns) |
| 2 | `router` | Intent classification + circuit breaker + active-learning sampling |
| 3 | `jit_booster` | Mandatory SOTA signal fetcher (Gemini-2.5-flash) |
| 3 | `executor` | Parallel fan-out (honours `max_workers`) |
| 3 | `scope_evaluator` | Pre-execution wave-plan analysis |
| 4 | `refinement` | Post-execution evaluation loop |
| 4 | `supervisor` | Two-stroke sub-pipeline |
| 4 | `vector_store` | In-process TF-IDF cosine-similarity store |
| 5 | `n_stroke` | Primary execution loop (up to 7 strokes) |
| 5 | `conversation` | Conversational intent discovery |
| 5 | `refinement_supervisor` | Autonomous healing |
| 6 | `branch_executor` | FORK/CLONE/SHARE async branch pipeline |
| 6 | `mandate_executor` | LLM-powered DAG node work-function factory |
| 6 | `model_garden` | 4-tier multi-provider model selector + consensus |
| 6 | `daemon` | Background ROI-scoring + autonomous proposal daemon |
| 7 | `gateway` | FastAPI Gateway providing External routing, Auth, SSE Streaming |
| 7 | `mcp_manager` | Dynamic Model Context Protocol tool execution + manifest bridge |

### Externals / Interactivity
| Module | Role |
|--------|------|
| `src/sdk/` | Python SDK (`TooLooClient`) for remote execution & SSE streaming |
| `src/api/` | FastAPI REST Gateway (`/v2/execute`, `/v2/stream`) |

### Supporting Modules

| Module | Role |
|--------|------|
| `engine/meta_architect.py` | Dynamic DAG synthesis with confidence proofs |
| `engine/model_selector.py` | Dynamic model escalation (4-tier) |
| `engine/mcp_manager.py` | MCP tool injection (7 built-in tools) |
| `engine/roadmap.py` | Graph-backed Roadmap Manager with semantic dedup |
| `engine/sandbox.py` | Mirror Sandbox Orchestrator (9-stage isolated evaluation) |
| `engine/engram_visual.py` | Visual Engram Generator → multi-layer SVG frontend |
| `engine/sota_ingestion.py` | SOTA Knowledge Ingestion Engine (Gemini-powered) |
| `engine/knowledge_banks/` | Four-bank SOTA knowledge system (Design/Code/AI/Bridge) |
| `engine/healing_guards.py` | Healing prescription guards |
| `engine/validator_16d.py` | 16-dimension output validator |
| `engine/local_slm_client.py` | Local SLM (Ollama) dispatch client |

---

## Core Laws (always enforced)

| # | Law | Rule |
|---|-----|------|
| 9 | No Hardcoded Credentials | All config loads via `engine/config.py` from `.env` |
| 14 | Circuit Breaker | Threshold `0.85` — hedge or invoke JITBooster below it |
| 17 | Stateless Processors | All nodes stateless for race-condition-free fan-out |
| 19 | Epistemic Humility | Confidence gate before every action; JITBooster for grounding |
| 20 | Autonomous Execution Authority | Proceeds when `AUTONOMOUS_EXECUTION_ENABLED=True` (default); three invariants: (1) OWASP scan every artefact, (2) writes sandboxed to `engine/`, (3) legal ops only. Advisory `consultation_recommended` SSE when confidence < 0.99. |

---

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Configure (copy template and fill in GCP / Anthropic keys)
cp .env.example .env

# Run the Governor Studio
python3 -m studio.api
# → opens http://localhost:8002

# Run the offline test suite (~4 s)
pytest tests/ --ignore=tests/test_ingestion.py

# Run self-improvement cycles (offline mode)
python3 run_cycles.py --cycles 3

# Run self-improvement cycles (live Vertex AI)
TOOLOO_LIVE_TESTS=1 python3 run_cycles.py --cycles 3

# Ouroboros autonomous cycle
python3 ouroboros_cycle.py --dry-run --components engine/router.py,engine/tribunal.py

# Run API Gateway
uvicorn src.api.main:app

# Test the Python SDK
python3 scripts/sdk_demo.py

# Run Agentic MCP Adversarial Training (Stage 2)
python3 scripts/adversarial_tool_training.py
```

---

## Async Execution

TooLoo V2 supports two N-Stroke execution strategies:

| Strategy | Endpoint | How it works |
|----------|----------|--------------|
| **Sync** (default) | `POST /v2/n-stroke` | Wave-ordered; all nodes in a wave complete before the next wave starts |
| **Async Fluid** | `POST /v2/n-stroke/async` | Dependency-resolved; each node fires the instant its own dependencies complete — no wave barriers |

```bash
# Sync (default)
curl -X POST http://localhost:8002/v2/n-stroke \
  -H 'Content-Type: application/json' \
  -d '{"intent":"BUILD","confidence":0.95,"value_statement":"build auth module","mandate_text":"build auth module"}'

# Async fluid
curl -X POST http://localhost:8002/v2/n-stroke/async \
  -H 'Content-Type: application/json' \
  -d '{"intent":"BUILD","confidence":0.95,"value_statement":"build auth module","mandate_text":"build auth module"}'
# Response includes: "execution_mode": "async_fluid"

# Benchmark sync vs async on the same mandate
curl http://localhost:8002/v2/n-stroke/benchmark
# Response: {"sync_ms": N, "async_ms": M, "delta_ms": N-M, "faster": "sync"|"async_fluid"}
```

The UI **Status** panel has a **⚡ Async N-Stroke** toggle and a **⏱ Benchmark** button.
When live mode is enabled (`TOOLOO_LIVE_TESTS=1`), the async path typically reduces
latency by 25–40% on DAGs with 6+ nodes and diamond-shaped dependency structures.

---

## How to Run Tests

```bash
# Standard offline suite (584 passed, ~4 s)
pytest tests/ --ignore=tests/test_ingestion.py

# Playwright UI tests (requires live server + Chromium)
pytest tests/test_playwright_ui.py --headed=false -v --timeout=60

# Include ingestion microservice tests (requires opentelemetry + backing services)
pytest tests/test_ingestion.py
```

Expected output (offline): **584 passed**, 1 warning, ~4 s

---

## Project Layout

```
engine/           ← Core cognitive DAG components (17 engine modules)
  knowledge_banks/  ← Four-bank SOTA knowledge system
studio/           ← FastAPI Governor Dashboard + SSE event bus
  static/           ← Single-page UI (index.html + assets)
tests/            ← 584-test offline suite
sandbox/          ← Escape-room test fixture (planted bugs for training)
psyche_bank/      ← Persistent cognitive rule store (.cog.json)
plans/            ← Architecture diagrams
adr/              ← Architecture Decision Records
docs/             ← Extended architecture documentation
```

---

## Self-Improvement System

TooLoo V2 includes a recursive self-improvement loop:

1. **Assessment** — `SelfImprovementEngine` reads each engine component source (3 000-char window) and calls Gemini-2.5-flash for structured `FIX N: file:line — desc\nCODE:\n<snippet>` suggestions.
2. **Tribunal gate** — every suggestion passes `Tribunal.evaluate()` before absorption.
3. **Absorption** — `BackgroundDaemon` queues approved FIX blocks; high-risk components (`tribunal`, `psyche_bank`, `router`) require explicit approval.
4. **Regression gate** — `SelfImprovementEngine._run_regression_gate()` runs the test suite after each application, rolling back on failure.
5. **Ouroboros** — `ouroboros_cycle.py` runs the full loop end-to-end; `run_cycles.py` batches N cycles with telemetry.

---

## Security

- All secrets and paths load exclusively from `.env` (Law 9).
- OWASP Tribunal scans every generated artefact (12 patterns incl. BOLA/IDOR, SSRF, SQLi, XSS).
- Path-traversal guard on all MCP file-access tools.
- No `eval()` / `exec()` / dynamic imports in logic bodies.
- GCP service-account key files are gitignored (blocks `*.sa-key.json`, `too-loo-zi8g7e-*.json`).

---

## Configuration (`.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `GCP_PROJECT_ID` | — | Vertex AI project |
| `GCP_REGION` | `us-central1` | Vertex AI region |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Path to SA key JSON |
| `VERTEX_DEFAULT_MODEL` | `gemini-2.5-flash` | Primary Gemini model |
| `ANTHROPIC_VERTEX_REGION` | `us-east5` | Claude on Vertex region |
| `STUDIO_PORT` | `8002` | Governor Dashboard port |
| `CIRCUIT_BREAKER_THRESHOLD` | `0.85` | Router circuit breaker |
| `AUTONOMOUS_EXECUTION_ENABLED` | `true` | Enable autonomous execution |
| `AUTONOMOUS_CONFIDENCE_THRESHOLD` | `0.99` | Confidence gate for advisory |
| `LOCAL_SLM_ENDPOINT` | `http://127.0.0.1:11434/api/generate` | Ollama endpoint |
| `LOCAL_SLM_MODEL` | `local/llama-3.2-3b-instruct` | Tier-0 local model |

See `.env.example` for the full list.
