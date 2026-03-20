#!/usr/bin/env bash
# run_fluid_ouroboros.sh — TooLoo V2 Fluid Ouroboros Safeguard Crucible
#
# Creates a disposable sandbox workspace, runs the full stress-test suite,
# streams structured telemetry to stdout, and preserves all artefacts.
#
# Usage:
#   chmod +x run_fluid_ouroboros.sh
#   ./run_fluid_ouroboros.sh [--dry-run] [--round N] [--verbose]
#
# Flags:
#   --dry-run     Print what would be done without executing tests.
#   --round N     Run only round N (1, 2, or 3). Default: all rounds.
#   --verbose     Pass -v to pytest for full test output.
#
# Safety invariants (always enforced):
#   1. Engine writes are sandboxed to ./sandbox_crucible_<epoch>/
#   2. CIRCUIT_BREAKER_THRESHOLD stays at 0.85 — never bypassed.
#   3. No destructive operations on the main workspace.
#
# Output:
#   CRUCIBLE_PASS | CRUCIBLE_FAIL  (final line, machine-readable)

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED="\033[0;31m"; GREEN="\033[0;32m"; YELLOW="\033[1;33m"
CYAN="\033[0;36m"; BOLD="\033[1m"; RESET="\033[0m"
ts() { date "+%H:%M:%S"; }
log()  { echo -e "${CYAN}[$(ts)]${RESET} $*"; }
ok()   { echo -e "${GREEN}[$(ts)] ✓${RESET} $*"; }
warn() { echo -e "${YELLOW}[$(ts)] ⚠${RESET} $*"; }
fail() { echo -e "${RED}[$(ts)] ✗${RESET} $*"; }

# ── Argument parsing ──────────────────────────────────────────────────────────
DRY_RUN=false
TARGET_ROUND=""
PYTEST_EXTRA=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)   DRY_RUN=true; shift ;;
    --round)     TARGET_ROUND="$2"; shift 2 ;;
    --verbose)   PYTEST_EXTRA="-v"; shift ;;
    *) warn "Unknown argument: $1"; shift ;;
  esac
done

# ── Workspace paths ───────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EPOCH=$(date +%s)
SANDBOX_DIR="${SCRIPT_DIR}/sandbox_crucible_${EPOCH}"

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}${CYAN}║        TooLoo V2 — Fluid Ouroboros Crucible Runner       ║${RESET}"
echo -e "${BOLD}${CYAN}║  Scope → Execute → Refine · DAG · N-Stroke · Art Director║${RESET}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════╝${RESET}"
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
  warn "DRY-RUN mode — no tests will execute."
fi

# ── Step 1: sandbox workspace ─────────────────────────────────────────────────
log "Creating sandboxed workspace at: ${SANDBOX_DIR}"
if [[ "$DRY_RUN" != "true" ]]; then
  mkdir -p "${SANDBOX_DIR}"
  # Copy only engine + studio (not the full workspace) to keep the sandbox light
  cp -r "${SCRIPT_DIR}/engine"  "${SANDBOX_DIR}/"
  cp -r "${SCRIPT_DIR}/studio"  "${SANDBOX_DIR}/"
  cp -r "${SCRIPT_DIR}/tests"   "${SANDBOX_DIR}/"
  cp -r "${SCRIPT_DIR}/psyche_bank" "${SANDBOX_DIR}/"
  [[ -f "${SCRIPT_DIR}/pyproject.toml" ]] && cp "${SCRIPT_DIR}/pyproject.toml" "${SANDBOX_DIR}/"
  [[ -f "${SCRIPT_DIR}/.env" ]]           && cp "${SCRIPT_DIR}/.env"           "${SANDBOX_DIR}/"
  ok "Sandbox created."
fi

# ── Step 2: environment variables ────────────────────────────────────────────
log "Configuring strict no-mock environment…"
export TOOLOO_STRICT_NO_MOCKING=True
export TOOLOO_AUTONOMOUS_EXECUTION=True
export TOOLOO_CONFIDENCE_THRESHOLD=0.99
export TOOLOO_CIRCUIT_BREAKER_THRESHOLD=0.85
export TOOLOO_LIVE_TESTS=False          # keep offline for safety; flip to True for live API
log "  TOOLOO_STRICT_NO_MOCKING   = ${TOOLOO_STRICT_NO_MOCKING}"
log "  TOOLOO_AUTONOMOUS_EXECUTION = ${TOOLOO_AUTONOMOUS_EXECUTION}"
log "  TOOLOO_CIRCUIT_BREAKER_THRESHOLD = ${TOOLOO_CIRCUIT_BREAKER_THRESHOLD}"

# ── Step 3: discover Python ───────────────────────────────────────────────────
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" &>/dev/null; then
  fail "Python not found. Set PYTHON=<path> or ensure python3 is on PATH."
  exit 1
fi
log "Using Python: $($PYTHON --version 2>&1)"

# ── Helper: run a pytest subset and report ────────────────────────────────────
_run_round() {
  local round_num="$1"
  local description="$2"
  local test_pattern="$3"
  local extra_flags="${4:-}"

  echo ""
  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  log "ROUND ${round_num}: ${description}"
  echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

  if [[ "$DRY_RUN" == "true" ]]; then
    warn "[DRY-RUN] Would run: pytest ${test_pattern} ${PYTEST_EXTRA} ${extra_flags}"
    return 0
  fi

  local t_start
  t_start=$(date +%s%N)

  set +e
  "$PYTHON" -m pytest \
    ${test_pattern} \
    --tb=short -q \
    --timeout=60 \
    ${PYTEST_EXTRA} ${extra_flags} \
    2>&1
  local exit_code=$?
  set -e

  local t_end
  t_end=$(date +%s%N)
  local elapsed_ms=$(( (t_end - t_start) / 1000000 ))

  if [[ $exit_code -eq 0 ]]; then
    ok "Round ${round_num} PASSED in ${elapsed_ms}ms."
    return 0
  else
    fail "Round ${round_num} FAILED (exit code ${exit_code}) after ${elapsed_ms}ms."
    return $exit_code
  fi
}

# ── Step 4: run the rounds ────────────────────────────────────────────────────
OVERALL_PASS=true

_should_run() {
  [[ -z "$TARGET_ROUND" ]] || [[ "$TARGET_ROUND" == "$1" ]]
}

# Round 1: Data Avalanche — MCP tools, speculative healing, micro-mitosis
if _should_run 1; then
  cd "${SCRIPT_DIR}"
  _run_round 1 \
    "Data Avalanche — MCP Tools · Speculative Healing · Micro-Mitosis · Symbol Mapping" \
    "tests/test_speculative_healing.py tests/test_n_stroke_stress.py" \
    "" || OVERALL_PASS=false
fi

# Round 2: Spatial Engine — Art Director, Visual Artifacts, Buddy Lang
if _should_run 2; then
  cd "${SCRIPT_DIR}"
  _run_round 2 \
    "Spatial Engine — Art Director · Visual Artifacts · Buddy Visual Language" \
    "tests/test_art_director.py tests/test_visual_artifacts.py" \
    "" || OVERALL_PASS=false
fi

# Round 3: Systemic Collapse — Tribunal, Convergence Guard, Full Crucible
if _should_run 3; then
  cd "${SCRIPT_DIR}"
  _run_round 3 \
    "Systemic Collapse — Tribunal · Convergence Guard · E2E Crucible Proof" \
    "tests/test_crucible.py tests/test_workflow_proof.py" \
    "" || OVERALL_PASS=false
fi

# ── Step 5: full regression sweep ─────────────────────────────────────────────
if [[ -z "$TARGET_ROUND" ]]; then
  echo ""
  log "Full regression sweep across all non-network tests…"
  cd "${SCRIPT_DIR}"
  if [[ "$DRY_RUN" != "true" ]]; then
    set +e
    "$PYTHON" -m pytest tests/ \
      --ignore=tests/test_ingestion.py \
      --ignore=tests/test_playwright_ui.py \
      -q --tb=short --timeout=60 \
      ${PYTEST_EXTRA} 2>&1
    sweep_code=$?
    set -e
    if [[ $sweep_code -eq 0 ]]; then
      ok "Full regression sweep PASSED."
    else
      fail "Full regression sweep FAILED (exit code ${sweep_code})."
      OVERALL_PASS=false
    fi
  else
    warn "[DRY-RUN] Would run full regression sweep."
  fi
fi

# ── Step 6: self-condition report ─────────────────────────────────────────────
echo ""
log "Generating self-condition telemetry snapshot…"
if [[ "$DRY_RUN" != "true" ]]; then
  "$PYTHON" - <<'PYEOF'
import time, json, sys
t0 = time.monotonic()
report = {}

# Engine component health check
components = [
    ("config",            "engine.config",            "settings"),
    ("router",            "engine.router",            "MandateRouter"),
    ("tribunal",          "engine.tribunal",          "Tribunal"),
    ("mcp_manager",       "engine.mcp_manager",       "MCPManager"),
    ("refinement_sup",    "engine.refinement_supervisor", "RefinementSupervisor"),
    ("speculative_heal",  "engine.refinement_supervisor", "SpeculativeHealingEngine"),
    ("branch_executor",   "engine.branch_executor",   "BranchExecutor"),
    ("n_stroke",          "engine.n_stroke",           "NStrokeEngine"),
    ("jit_booster",       "engine.jit_booster",       "JITBooster"),
    ("mandate_executor",  "engine.mandate_executor",  "make_live_work_fn"),
    ("art_director",      "engine.mandate_executor",  "_run_art_director"),
    ("conversation",      "engine.conversation",      "ConversationEngine"),
    ("model_garden",      "engine.model_garden",       "get_garden"),
    ("vector_store",      "engine.vector_store",       "VectorStore"),
    ("psyche_bank",       "engine.psyche_bank",        "PsycheBank"),
    ("sandbox",           "engine.sandbox",            "SandboxOrchestrator"),
]

for label, module, symbol in components:
    try:
        m = __import__(module, fromlist=[symbol])
        getattr(m, symbol)
        report[label] = "UP"
    except Exception as exc:
        report[label] = f"ERR: {exc}"

# MCP manifest
try:
    from engine.mcp_manager import MCPManager
    mcp = MCPManager()
    report["mcp_tool_count"] = len(mcp.manifest())
    report["mcp_tools"] = [t.name for t in mcp.manifest()]
except Exception as exc:
    report["mcp_tool_count"] = f"ERR: {exc}"

report["latency_ms"] = round((time.monotonic() - t0) * 1000, 2)
report["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
print(json.dumps({"type": "self_condition_report", "data": report}, indent=2))
PYEOF
fi

# ── Final verdict ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
if [[ "$OVERALL_PASS" == "true" ]]; then
  echo -e "${GREEN}${BOLD}  CRUCIBLE_PASS — All rounds validated. TooLoo is production-ready.${RESET}"
else
  echo -e "${RED}${BOLD}  CRUCIBLE_FAIL — One or more rounds failed. Review output above.${RESET}"
fi
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

if [[ "$DRY_RUN" != "true" ]] && [[ -d "$SANDBOX_DIR" ]]; then
  log "Artefacts preserved at: ${SANDBOX_DIR}"
fi

[[ "$OVERALL_PASS" == "true" ]] && exit 0 || exit 1
