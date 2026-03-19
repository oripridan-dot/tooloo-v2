# TooLoo V2 — Copilot System Instructions: Pure DAG Cognitive OS

You are operating within the **TooLoo V2 Pure DAG Cognitive OS**. Your primary
function is to enforce architectural laws, ensure epistemic humility, and
facilitate the autonomous, recursive, and parallel execution of engineering tasks
via the N-Stroke Engine.

Every task follows the **Scope → Execute → Refine** cycle defined in
`engine/scope_evaluator.py` and `engine/refinement.py`. Apply this cycle to ALL
work: code generation, debugging, and refactoring.

---

## 1. Session Lifecycle (MANDATORY)

### Session Start
At the beginning of every session, **read `PIPELINE_PROOF.md`** to:
- Establish context from previous sessions.
- Identify outstanding blockers or open work.
- Align with the current DAG wave plan.

### Session End
Before closing, **append a structured entry** to the Session Log in
`PIPELINE_PROOF.md` using this exact format:

```markdown
### Session YYYY-MM-DD — <one-line summary>
**Branch / commit context:** <branch or "untracked">
**Tests at session start:** <N passed / M failed>
**Tests at session end:** <N passed>
**What was done:**
- bullet points
**What was NOT done / left open:**
- bullet points
**JIT signal payload (what TooLoo learned this session):**
- discoveries, patterns, rules
```

The **JIT signal payload** must contain concrete, actionable heuristics, SOTA
discoveries, or rules that can be immediately utilised by `JITBooster` or
`PsycheBank` in future iterations.

---

## 2. Core Architectural Laws (always enforced)

| Law | Rule |
|-----|------|
| **9 — No Hardcoded Credentials** | All config and credentials load via `engine/config.py` from `.env`. Never hardcode secrets or paths. |
| **14 — Circuit Breaker** | `CIRCUIT_BREAKER_THRESHOLD = 0.85`. If confidence falls below this, hedge, clarify, or invoke `JITBooster` before proceeding. |
| **17 — Stateless Processors** | All processing nodes and agents must be stateless to allow race-condition-free fan-out via `JITExecutor` / `ThreadPoolExecutor`. |
| **19 — Epistemic Humility** | Before executing any action, pass a confidence gate. If unsure, invoke `JITBooster` to ground the action in 2026 SOTA signals. |
| **20 — Autonomous Execution Authority** | Execution proceeds autonomously when `AUTONOMOUS_EXECUTION_ENABLED=True` (the default). Three inviolable safety invariants always hold: (1) Tribunal OWASP scan on every artefact, (2) writes sandboxed to `engine/` components only, (3) legal/non-criminal operations only. A `consultation_recommended` SSE event is emitted (advisory, non-blocking) when confidence < `AUTONOMOUS_CONFIDENCE_THRESHOLD` (0.99). `--dry-run` remains the explicit opt-out. |

---

## 3. Mandatory Execution Workflow

### Step 1 — Action Scope Evaluation (BEFORE any code is written)

Evaluate scope by:
- **Enumerating micro-processes**: smallest independent work units (DAG nodes).
- **Mapping dependencies**: topological waves.
- **Estimating parallelism**: concurrent vs. serial.
- **Identifying risk surface**: highest-risk nodes get extra scrutiny.
- **Stating strategy**: *serial* / *parallel* / *deep-parallel*.

Output this summary before writing any code:

```
Scope: N nodes · W waves · max ×P parallel · strategy: <strategy>
Risk: <which nodes are highest risk and why>
Plan: [node-1] → [node-2 ‖ node-3] → [node-4]
```

### Step 2 — SOTA Grounding (JITBooster — mandatory pre-execution)

TooLoo does not guess; it researches.

- **Invoke `JITBooster`** before executing any plan to fetch 2026 SOTA signals
  via the `google-genai` SDK (Gemini-2.5-flash). Falls back to structured
  catalogue when Gemini is unavailable.
- Boost formula: `boost_delta = min(N_signals × 0.05, 0.25)`. Cap at 1.0.
- Every `/v2/mandate` and `/v2/chat` call **must** run `JITBooster.fetch()`
  before Tribunal and plan. Responses always include a `jit_boost` field.
- Use latest standards verified by the booster (e.g. `ort-web` + WebNN for
  browser ONNX inference, not legacy pathways).

### Step 3 — OWASP Tribunal (mandatory security scan)

Security is non-negotiable.

- Every generated artifact, especially those involving dynamic execution
  (`eval()`, `exec()`, Web Audio Worklets), **must** be scanned by
  `Tribunal.evaluate()`.
- **Poison detected** → replace offending logic with a tombstone comment,
  capture the rule in `psyche_bank/forbidden_patterns.cog.json`, halt that
  execution path.
- Tribunal runs on every DAG node, not just final output.

### Step 4 — Execution (wave-ordered, parallels batched)

- Execute in wave order via the `NStrokeEngine`. All mandates are channelled
  through this engine (`engine/n_stroke.py`).
- Within a wave, invoke independent tool calls **in the same parallel batch**
  (`multi_replace_string_in_file` for edits, parallel reads, etc.).
- Do NOT execute later waves until the current wave is complete and verified.
- **DAG acyclicity**: `CognitiveGraph.add_edge` raises `CycleDetectedError`
  and rolls back on any cycle attempt. Never introduce cycles.
- **Isolated fan-out**: sub-tasks run via `JITExecutor` (backed by
  `ThreadPoolExecutor`). All instances must be perfectly isolated (stateless,
  Law 17). Shared context goes through `SharedBlackboard` or `CIPEnvelope`.

### Step 5 — Autonomous Healing (on node failure)

- When a DAG node reaches `NODE_FAIL_THRESHOLD = 3` failures, trigger
  `RefinementSupervisor`.
- Healing pipeline: `MCPManager.read_error()` → `MCPManager.web_lookup()` →
  synthesise `HealingPrescription` → Tribunal poison-guard → inject as
  `[retry-signal]` for next stroke.
- **Do not retry the same failing approach** — change strategy first.

### Step 6 — Evaluate-and-Refine Loop (AFTER each build / change set)

- **Check success rate**: did all units complete without errors?
- **Identify brittle nodes**: any unit requiring multiple attempts or producing
  linting/type/test errors.
- **Run `get_errors`** after every file edit to catch regressions immediately.
- **Produce a refinement verdict**: `pass` / `warn` / `fail`.
- **State recommendations** for the follow-up pass.
- **Re-run failed units only** after changing the approach.

---

## 4. Engine Conventions

| Component | File | Role |
|---|---|---|
| `ScopeEvaluator` | `engine/scope_evaluator.py` | Pre-execution wave-plan analysis |
| `RefinementLoop` | `engine/refinement.py` | Post-execution evaluation loop |
| `JITExecutor` | `engine/executor.py` | Parallel fan-out (honours `max_workers`) |
| `TopologicalSorter` | `engine/graph.py` | Wave planner; enforces DAG acyclicity |
| `Tribunal` | `engine/tribunal.py` | OWASP poison scanner (runs on every node) |
| `MandateRouter` | `engine/router.py` | Intent classification + circuit breaker |
| `JITBooster` | `engine/jit_booster.py` | Mandatory SOTA signal fetcher |
| `NStrokeEngine` | `engine/n_stroke.py` | Primary execution loop (up to 7 strokes) |
| `RefinementSupervisor` | `engine/refinement_supervisor.py` | Autonomous healing |
| `MCPManager` | `engine/mcp_manager.py` | MCP tool injection (6 built-in tools) |
| `ModelSelector` | `engine/model_selector.py` | Dynamic model escalation (4-tier) |
| `TwoStrokeEngine` | `engine/supervisor.py` | Two-stroke sub-pipeline |
| `PsycheBank` | `engine/psyche_bank.py` | Thread-safe `.cog.json` rule store |
| `Config` | `engine/config.py` | Single source of truth — loads from `.env` |

- All new engine modules go in `engine/`. No external dependencies beyond
  stdlib + networkx + fastapi.
- Every new execution path **must** pass through `Tribunal.evaluate()`.
- The circuit breaker (`CIRCUIT_BREAKER_THRESHOLD = 0.85`) must never be bypassed.
- All `.cog.json` rule files live in `psyche_bank/`.
- Singletons that inject `broadcast_fn` must be declared **after** `_broadcast`
  in `studio/api.py` — this is a hard ordering invariant.

---

## 5. Security Rules (always enforced)

- Never hardcode secrets, tokens, or passwords in any file.
- No `eval()`, `exec()`, or dynamic imports in logic bodies.
- No raw SQL string concatenation — use parameterised queries.
- All user input entering engine pipelines must be validated at the
  `studio/api.py` boundary.
- Path-traversal guard on all file-access MCP tools (no `../` escape).
- All text rendered from API data must pass through `esc()` before `innerHTML`.

---

## 6. API Contract

- New endpoints go under `/v2/` prefix.
- All mandate responses include: `mandate_id`, `route`, `scope`, `plan`,
  `execution`, `refinement`, `latency_ms`.
- SSE event types: `route`, `tribunal`, `plan`, `scope`, `execution`,
  `refinement`, `heartbeat`, `jit_boost`, `n_stroke_start`, `model_selected`,
  `healing_triggered`, `n_stroke_complete`, `satisfaction_gate`,
  `preflight`, `midflight`, `process_1_draft`, `process_2_execute`,
  `pipeline_start`, `loop_complete`, `intent_clarification`, `intent_locked`,
  `self_improve`.

---

## 7. UI Conventions

- Design tokens live in the `:root` block of `studio/static/index.html`.
- New panels follow the existing sidebar pattern: add a nav button, a
  `<section class="view">`, and the matching JS loader.
- All text rendered from API data must pass through `esc()` before `innerHTML`.
- GSAP `transformOrigin` on SVG elements must use SVG user-unit coordinates
  (e.g. `'380 240'`), not CSS `'center center'`.
