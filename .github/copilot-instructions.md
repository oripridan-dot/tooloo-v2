# TooLoo V2 — Copilot Default Execution Workflow

Every task in this repo follows the **Scope → Execute → Refine** cycle defined
in `engine/scope_evaluator.py` and `engine/refinement.py`.
Apply this cycle to ALL work you perform here, including code generation,
debugging, and refactoring.

---

## Mandatory Execution Workflow

### 1. Action Scope Evaluation (BEFORE any code is written)

Before starting any task, explicitly evaluate its scope:

- **Enumerate micro-processes**: break the task into the smallest independent
  work units (analogous to DAG nodes). State them as a list.
- **Map dependencies**: identify which units must complete before others can
  start (analogous to topological waves).
- **Estimate parallelism**: which units can run concurrently, which are serial.
- **Identify risk surface**: which units are most likely to introduce bugs,
  security issues, or breaking changes — address those first or with extra care.
- **State the strategy**: *serial* (mostly sequential), *parallel* (single wave),
  or *deep-parallel* (wide waves with high concurrency).
- **Output a short scope summary** before writing any code, in the format:

  ```
  Scope: N nodes · W waves · max ×P parallel · strategy: <strategy>
  Risk: <which nodes are highest risk and why>
  Plan: [node-1] → [node-2 ‖ node-3] → [node-4]
  ```

### 2. Execution (wave-ordered, parallels batched)

- Execute the plan in wave order.
- Within a wave, invoke independent tool calls **in the same parallel batch**
  (use `multi_replace_string_in_file` for simultaneous edits, parallel reads, etc.).
- Do NOT execute later waves until the current wave is complete and verified.

### 3. Evaluate-and-Refine Loop (AFTER each build / change set)

After completing each wave (or at the end of the full task):

- **Check success rate**: did all units complete without errors?
- **Identify slow / brittle nodes**: any unit that took multiple attempts or
  produced linting/type/test errors.
- **Run `get_errors`** after every file edit to catch regressions immediately.
- **Produce a refinement verdict**: `pass` / `warn` / `fail`.
- **State recommendations**: what should be improved in a follow-up pass.
- **Re-run failed units only** if the rerun is likely to succeed (do not retry
  the same failing approach — change it first).

---

## Engine Conventions

| Component | File | Role |
|---|---|---|
| `ScopeEvaluator` | `engine/scope_evaluator.py` | Pre-execution plan analysis |
| `RefinementLoop` | `engine/refinement.py` | Post-execution evaluation |
| `JITExecutor` | `engine/executor.py` | Parallel fan-out (honours `max_workers` from scope) |
| `TopologicalSorter` | `engine/graph.py` | Wave planner |
| `Tribunal` | `engine/tribunal.py` | OWASP poison scanner (runs on every node) |
| `MandateRouter` | `engine/router.py` | Intent classification + circuit breaker |

- All new engine modules go in `engine/`. No external dependencies beyond stdlib + networkx + fastapi.
- Every new execution path **must** pass through `Tribunal.evaluate()`.
- The circuit breaker (`CIRCUIT_BREAKER_THRESHOLD = 0.85`) must never be bypassed.
- All `.cog.json` rule files live in `psyche_bank/`.

## Security Rules (always enforced)

- Never hardcode secrets, tokens, or passwords in any file.
- No `eval()`, `exec()`, or dynamic imports in logic bodies.
- No raw SQL string concatenation — use parameterised queries.
- All user input entering engine pipelines must be validated at the `studio/api.py` boundary.

## API Contract

- New endpoints go under `/v2/` prefix.
- All mandate responses include: `mandate_id`, `route`, `scope`, `plan`, `execution`, `refinement`, `latency_ms`.
- SSE event types: `route`, `tribunal`, `plan`, `scope`, `execution`, `refinement`, `heartbeat`.

## UI Conventions

- Design tokens live in the `:root` block of `studio/static/index.html`.
- New panels follow the existing 4-panel sidebar pattern: add a nav button, a `<section class="view">`, and the matching JS loader.
- All text rendered from API data must pass through `esc()` before being set as innerHTML.
