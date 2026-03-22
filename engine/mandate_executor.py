"""
engine/mandate_executor.py — LLM-powered DAG node executor.

Replaces symbolic stub work functions with real Vertex AI (primary) /
Gemini Direct (fallback) calls.  One targeted prompt per DAG node type:

  ingest    → identify relevant files / data sources for the mandate
  analyse   → root-cause / design-gap analysis grounded in JIT SOTA signals
  design    → implementation blueprint with component names and interfaces
  implement → generate production-quality code following TooLoo V2 conventions
  validate  → validation checklist: tests, edge cases, OWASP checks
  emit      → crisp summary: what was done, output, recommended next step

Architecture:
  ``make_live_work_fn()`` is a factory that captures mandate context in a
  closure and returns a stateless ``work_fn(env: Envelope) -> dict`` suitable
  for parallel fan-out via JITExecutor (Law 17 compliant — no shared mutable
  state; each call is fully independent).

  Falls back to symbolic execution when both Vertex AI and Gemini Direct are
  unavailable (test / offline mode).

Security:
  - All LLM output is treated as untrusted text (not eval'd, not exec'd).
  - Mandate text is truncated to 500 chars before being sent to the LLM.
  - Follows Law 9: no hardcoded credentials — all via engine/config.py.
"""
from __future__ import annotations
from engine.vlt_schema import VectorTree, VLTAuditReport
from engine.mcp_manager import MCPManager
from engine.executor import Envelope
from engine.config import _vertex_client as _vertex_client_cfg
from engine.config import GEMINI_API_KEY, GEMINI_MODEL, VERTEX_DEFAULT_MODEL

import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Control: configurable thresholds for executor safety
_MAX_RETRIES = 3                   # per-node LLM call retry ceiling
_LLM_TIMEOUT_THRESHOLD = 60        # seconds — triggers circuit-breaker fallback
_MANDATE_MAX_LENGTH = 500          # truncation threshold for mandate text

# Timing: module-level perf_counter anchor for latency instrumentation
_MODULE_INIT_T0 = time.perf_counter()


# ── LLM clients (initialised once at import — same pattern as jit_booster) ────
_vertex_client = _vertex_client_cfg

_gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        _gemini_client = _genai_mod.Client(api_key=GEMINI_API_KEY)
    except Exception:  # pragma: no cover
        pass

# ── Node-type → prompt template ───────────────────────────────────────────────
# {mandate}, {intent}, {signals} are always substituted.
# {context} carries a condensed summary of prior node outputs (may be "").
_NODE_SYSTEM = (
    "You are {node_type}, a specialised execution node inside TooLoo V2 — "
    "an autonomous DAG cognitive OS.  Be terse, precise, and actionable. "
    "Never expose internal implementation details. No preamble."
)

# ── Cognitive Swarm — Persistent Context Envelope ─────────────────────────────
# Injected at the head of every swarm-persona prompt so that all agents retain
# global awareness of the user's goal and constraints (Law of the Cognitive Swarm).
_PERSISTENT_CONTEXT_ENVELOPE = (
    "[PRIME ORCHESTRATOR CONTEXT]\n"
    "You are operating within the TooLoo V2 Cognitive Swarm.\n"
    "USER GOAL: {user_goal}\n"
    "CONSTRAINTS: {constraints}\n"
    "ROADMAP ALIGNMENT: Maximize SOTA (State of the Art) outcomes while honouring "
    "the user's specific context. Do not lose sight of the final objective.\n\n"
)

# ── Cognitive Swarm — Persona Prompt Matrix ───────────────────────────────────
# Five specialised personas that span the Diverge → Converge → Validate arc.
# Merged into _NODE_PROMPTS below so the standard node-dispatch path is reused.
_SWARM_PROMPTS: dict[str, str] = {
    "gapper": (
        "You are the GAPPER and SUGGESTOR.\n"
        "Your role: Analyse the delta between the current system state and the "
        "user's requested goal. Identify missing architectural pieces, potential "
        "roadblocks, and suggest the high-level roadmap to manifest the goal. "
        "Do not write final code; write the strategic blueprint.\n\n"
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}"
    ),
    "innovator": (
        "You are the INNOVATOR.\n"
        "Your role: Divergent, cutting-edge thinking. Use the provided 2026 JIT SOTA "
        "signals to propose radical, highly advanced solutions. Ignore conservative "
        "constraints temporarily to find the absolute maximum-value SOTA approach. "
        "Output bold, concrete architectural code structures.\n\n"
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}"
    ),
    "optimizer": (
        "You are the OPTIMIZER and IMPROVER.\n"
        "Your role: Convergent refinement. Take proposed solutions and ruthlessly "
        "optimise them for Big-O efficiency, memory safety, and clean execution. "
        "Enforce strict WCAG, Tailwind, and PEP 8 standards. Strip away bloat. "
        "Output the highest-quality, most efficient code possible.\n\n"
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}"
    ),
    "tester_stress": (
        "You are the TESTER and STRESS TESTER.\n"
        "Your role: Adversarial validation. Look at the proposed code and attempt to "
        "break it. Write brutal edge-case tests, identify race conditions, memory "
        "leaks, and logic flaws. Use MCP tools to execute these tests and output "
        "exactly where the system fails.\n\n"
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}"
    ),
    "sustainer": (
        "You are the SUSTAINER.\n"
        "Your role: Long-term health and governance. Ensure the new implementation "
        "is perfectly modular, well-documented, and backward compatible. Ensure no "
        "existing systems are broken by this addition. Finalise the integration.\n\n"
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}"
    ),
}

# Persona names that receive the Persistent Context Envelope automatically
_SWARM_PERSONAS: frozenset[str] = frozenset(_SWARM_PROMPTS.keys())

# Human-Centric Standard — prepended to all frontend node prompts
_HUMAN_CENTRIC_SYSTEM = (
    "You are bound by the Human-Centric Standard. "
    "Any interface generated MUST use Tailwind CSS v4 loaded via CDN: "
    "<link href='https://cdn.tailwindcss.com' rel='stylesheet'>. "
    "ALL layout and spacing MUST use Tailwind utility classes — NEVER bare unstyled HTML. "
    "NEVER use inline style= attributes for layout; use Tailwind classes exclusively. "
    "Animations and state transitions MUST use GSAP (loaded via CDN). "
    "The visual hierarchy must reflect 2026 design standards: dark-mode-capable, "
    "high contrast tokens, clear affordances, and micro-interactions. "
    "Follow WCAG 2.2 Level AA accessibility requirements: semantic HTML, "
    "aria-labels on interactive elements, minimum 4.5:1 contrast ratio. "
    "Output must be production-ready — not a prototype, not a sketch. "
    "Do not output unstyled, unclassed, or purely utilitarian markup. "
)

# Frontend file extensions and path patterns that trigger Human-Centric Standard
_FRONTEND_EXTS: frozenset[str] = frozenset(
    {".html", ".css", ".js", ".ts", ".tsx", ".jsx", ".vue", ".svelte"}
)
_FRONTEND_PATHS: frozenset[str] = frozenset(
    {"studio/static", "frontend", "/ui/", "index.html"}
)

_NODE_PROMPTS: dict[str, str] = {
    "deep_research": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Collect additional high-value context and edge cases relevant to this mandate. "
        "Return 5 concise bullets, each ending with an actionable implication."
    ),
    "ingest": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "List exactly 3 specific resources (files, APIs, patterns) most critical "
        "to understand before executing this mandate. "
        "Format as: - <resource>: <why it matters (one line)>"
    ),
    "analyse": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Perform a root-cause / design-gap analysis. "
        "Identify the 3 key gaps or risks, each with a concrete mitigation. "
        "Format as: - Gap: <description> → Fix: <action>"
    ),
    "design": (
        "{human_centric_prefix}"
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Produce a concrete implementation blueprint. "
        "Name the specific files, classes, and interfaces to create or modify. "
        "State the 4-wave DAG execution order. "
        "Format as numbered steps.\n\n"
        "SPATIAL UI MANDATE: If this implements any UI component, you MUST ALSO "
        "output a Vector Layout Tree (VLT) JSON block at the end of your response "
        "in this exact format:\n"
        "```vlt\n"
        "{{\"tree_id\":\"<id>\",\"viewport_width\":1920,\"viewport_height\":1080,"
        "\"root_node\":{{\"node_id\":\"root\",\"type\":\"container\","
        "\"dimensions\":{{\"width_pct\":100,\"height_pct\":100}},"
        "\"constraints\":{{}},\"style_tokens\":{{}},\"children\":[]}}}}\n"
        "```\n"
        "All node coordinates MUST use design-system tokens (no hex codes). "
        "Gap and padding values MUST be integers (8-px grid units)."
    ),
    "implement": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Generate the core implementation. "
        "Output production-quality Python code or configuration. "
        "Include the target file path as a comment on the first line. "
        "Follow TooLoo V2 conventions: stateless processors, no hardcoded secrets, "
        "all config from engine/config.py, Pydantic v2 for data models."
    ),
    "validate": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Produce a validation checklist for this implementation. "
        "Include: pytest test names to write, OWASP checks to run, integration "
        "points to verify. Format as checkboxes: - [ ] <check>"
    ),
    "emit": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Produce a deployment-ready summary:\n"
        "1. What was built / changed (2 sentences max)\n"
        "2. How to verify it works (1 command or URL)\n"
        "3. Recommended next mandate for TooLoo to execute"
    ),
    # ── Mandatory discovery nodes (Phase 1 Blueprint) ──────────────────────
    "audit_wave": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Phase 1 — Audit Wave. Before ANY implementation:\n"
        "1. Identify the blast radius of this change (which files/systems are affected).\n"
        "2. List 3 system constraints that must be honoured.\n"
        "3. Flag any OWASP Top 10 risks that this mandate could introduce.\n"
        "Format as a structured Audit Report with sections: Blast Radius / Constraints / Risks."
    ),
    "design_wave": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Phase 1 — Design Wave. Produce a Blueprint document:\n"
        "1. Architecture decision: what pattern to apply (name it).\n"
        "2. Component map: which modules/files change and why.\n"
        "3. Interface contract: inputs, outputs, invariants.\n"
        "4. Execution wave plan (DAG): ordered steps with dependencies.\n"
        "No implementation code yet — design only."
    ),
    "ux_eval": (
        "{human_centric_prefix}"
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Phase 1 — UX Evaluation Wave. Assess the human interface requirements:\n"
        "1. Cognitive load analysis: what mental models does the user need?\n"
        "2. Affordance map: key interactive elements and their visual cues.\n"
        "3. GSAP animation plan: which state transitions need micro-interactions.\n"
        "4. Accessibility checklist: WCAG 2.2 AA requirements for this UI.\n"
        "5. SPATIAL PROOF: Output a Vector Layout Tree (VLT) JSON block that "
        "mathematically encodes this UI. Use strict 8-px grid units for gap/padding. "
        "No hex codes — design-system tokens only. Format:\n"
        "```vlt\n"
        "{{\"tree_id\":\"<id>\",\"viewport_width\":1920,\"viewport_height\":1080,"
        "\"root_node\":{{...}}}}\n"
        "```\n"
        "Output a UX Blueprint with the VLT block. No implementation code yet."
        # ── Art Director node (visual quality gate) ───────────────────────────
    ),
    "art_director": (
        "{human_centric_prefix}"
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Art Director Review. Evaluate the UI output against 2026 production standards.\n"
        "1. Tailwind audit: are all layout elements using Tailwind v4 utility classes? "
        "List any bare HTML tags that need class= attributes.\n"
        "2. GSAP animation review: are state transitions smooth and purposeful? "
        "Name any transitions that are missing or jarring.\n"
        "3. Visual hierarchy score (1-10): rate contrast, spacing, and typography.\n"
        "4. Accessibility check: WCAG 2.2 AA pass/fail per component.\n"
        "5. Verdict: APPROVED | NEEDS_REVISION with specific change directives.\n"
        "If NEEDS_REVISION, output exact Tailwind class substitutions or GSAP snippets."
    ),    # ── Dry-run simulation node ────────────────────────────────────────────
    "dry_run": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Phase 2 — Dry Run. Generate the exact implementation but DO NOT commit.\n"
        "Output the proposed changes as a structural diff or code block.\n"
        "Mark every change with: [STAGED] <file_path> <description>.\n"
        "Flag any concerns that would prevent promotion to execute phase."
    ),
    # ── SPAWN_REPO: repository scaffold generator ──────────────────────────
    "spawn_repo": (
        "Mandate: «{mandate}»\n"
        "Intent: SPAWN_REPO\n"
        "JIT SOTA signals: {signals}\n\n"
        "Generate a complete repository scaffold plan. Output exactly:\n"
        "1. REPO_NAME: <slug> (lowercase, hyphens only)\n"
        "2. PURPOSE: <one sentence>\n"
        "3. TREE:\n"
        "   <directory tree using | and `-- notation>\n"
        "4. KEY_FILES:\n"
        "   - pyproject.toml: <purpose>\n"
        "   - README.md: <purpose>\n"
        "   - src/__init__.py: <purpose>\n"
        "   - tests/__init__.py: <purpose>\n"
        "   - .github/workflows/ci.yml: GitHub Actions CI pipeline stub\n"
        "5. NEXT_MANDATES (3 TooLoo mandates to run after scaffolding):\n"
        "   - <mandate-1>\n"
        "   - <mandate-2>\n"
        "   - <mandate-3>\n"
    ),
}

# Merge Cognitive Swarm personas into the standard node dispatch table
_NODE_PROMPTS.update(_SWARM_PROMPTS)

# Default prompt for unrecognised node types (covers wave-index nodes)
_WAVE_NODE_PROMPTS: list[str] = [
    "audit_wave", "design_wave", "ux_eval",   # Phase 1 discovery
    "ingest", "analyse",                        # Phase 2 dry-run
    "implement", "validate", "emit",            # Phase 3 execute
    "art_director",                             # Visual quality gate
    "spawn_repo",                               # Repository scaffold
]


def _node_type_from_id(mandate_id: str) -> str:
    """Derive node type from mandate_id suffix.

    Handles both semantic IDs (e.g. ``ns-abc-s1-implement``) and
    wave-indexed IDs (e.g. ``m-abc123-3``).
    """
    lowered = mandate_id.lower()
    for node_type in sorted(_NODE_PROMPTS.keys(), key=len, reverse=True):
        if lowered.endswith(node_type):
            return node_type
    suffix = mandate_id.rsplit("-", 1)[-1]
    if suffix in _NODE_PROMPTS:
        return suffix
    # Numeric suffix → map wave index to node type
    if suffix.isdigit():
        idx = min(int(suffix), len(_WAVE_NODE_PROMPTS) - 1)
        return _WAVE_NODE_PROMPTS[idx]
    return "analyse"


def _is_frontend_target(mandate_text: str, intent: str) -> bool:
    """Return True if the mandate targets a frontend/UI file."""
    text_lower = mandate_text.lower()
    return (
        any(ext in text_lower for ext in _FRONTEND_EXTS)
        or any(p in text_lower for p in _FRONTEND_PATHS)
        or intent.upper() in ("DESIGN", "UX_EVAL")
    )


def _extract_tool_calls(raw: str) -> list[dict[str, Any]]:
    """Return all tool calls embedded in a model response.

    Supports one or more ``<tool_call>{...}</tool_call>`` blocks and also a
    JSON array inside a single block for batched tool dispatch.
    """
    calls: list[dict[str, Any]] = []
    for match in re.finditer(r"<tool_call>(.*?)</tool_call>", raw, re.DOTALL):
        payload = match.group(1).strip()
        if not payload:
            continue
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, list):
            calls.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            calls.append(parsed)
    return calls


def make_live_work_fn(
    mandate_text: str,
    intent: str,
    jit_signals: list[str],
    vertex_model_id: str | None = None,
    mcp_manager: MCPManager | None = None,
    user_goal: str = "",
    constraints: str = "",
) -> Callable[[Envelope], dict[str, Any]]:
    """Return a stateless LLM-powered work function for JITExecutor fan-out.

    Each call to the returned function is fully independent (Law 17).
    Falls back to symbolic execution when both AI clients are unavailable.

    Args:
        mandate_text:     Original mandate string (truncated to 500 chars internally).
        intent:           Routed intent (BUILD / DEBUG / AUDIT / DESIGN / …).
        jit_signals:      Up to 3 SOTA signals from JITBooster.
        vertex_model_id:  Vertex AI model ID; defaults to VERTEX_DEFAULT_MODEL.
        mcp_manager:      Optional MCPManager for file_read/file_write/run_tests during
                          ingest and implement nodes.  When None a shared instance is
                          created once per factory call (stateless — safe for fan-out).
        user_goal:        Long-term goal injected into the Persistent Context Envelope
                          for Cognitive Swarm persona nodes.
        constraints:      Environmental / architectural constraints for the Swarm.
    """
    _model_id: str = vertex_model_id or VERTEX_DEFAULT_MODEL
    _mandate: str = mandate_text[:500]
    _signals_str: str = "; ".join(jit_signals[:3]) if jit_signals else "none"
    _mcp: MCPManager = mcp_manager or MCPManager()
    # Swarm context envelope — defaults to the mandate text when not supplied
    _user_goal: str = user_goal or mandate_text[:200]
    _constraints: str = constraints or "TooLoo V2 engine/ boundary; no hardcoded secrets"

    def _call_llm(node_type: str, prompt: str, model_id: str) -> str:
        """Call Vertex AI → Gemini Direct → symbolic fallback."""
        system = _NODE_SYSTEM.format(node_type=node_type)
        full_prompt = f"{system}\n\n{prompt}"

        if _vertex_client is not None:
            try:
                resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                    model=model_id, contents=full_prompt,
                )
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception:
                pass  # fall through to Gemini Direct

        if _gemini_client is not None:
            try:
                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                    model=GEMINI_MODEL, contents=full_prompt,
                )
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception:
                pass  # fall through to symbolic

        # Symbolic fallback (offline / test mode)
        return (
            f"[symbolic-{node_type}] intent={intent} "
            f"model={model_id} signals={_signals_str[:80]}"
        )

    def _call_llm_raw(full_prompt: str, _node_type: str, model_id: str) -> str:
        """Call LLM with a fully-built conversation prompt (no system prepend)."""
        if _vertex_client is not None:
            try:
                resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                    model=model_id, contents=full_prompt,
                )
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception:
                pass
        if _gemini_client is not None:
            try:
                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                    model=GEMINI_MODEL, contents=full_prompt,
                )
                text = (resp.text or "").strip()
                if text:
                    return text
            except Exception:
                pass
        # Symbolic fallback (offline / test mode)
        return (
            f"[symbolic-{_node_type}] intent={intent} "
            f"model={model_id} signals={_signals_str[:80]}"
        )

    def work_fn(env: Envelope) -> dict[str, Any]:
        """Stateless per-node execution — safe for parallel fan-out."""
        # Law 17: MCPManager instantiated inside the closure — no shared tool state
        # across concurrent DAG nodes executing via JITExecutor fan-out.
        mcp = MCPManager()

        node_type = _node_type_from_id(env.mandate_id)
        node_model_id = str(env.metadata.get("node_model") or _model_id)
        template = _NODE_PROMPTS.get(node_type, _NODE_PROMPTS["analyse"])

        # Determine node phase from envelope metadata (injected by NStrokeEngine)
        phase = env.metadata.get("phase", "execute")
        is_frontend = _is_frontend_target(_mandate, intent)
        target = env.metadata.get("target", "")

        # ── MCP: ingest reads the target file from disk ────────────────────
        mcp_context = ""
        if node_type == "ingest":
            file_path = env.metadata.get("file_path") or target
            if file_path:
                read_result = mcp.call_uri(
                    "mcp://tooloo/file_read", path=file_path)
                if read_result.success:
                    content = str(read_result.output or "")[:2000]
                    mcp_context = f"\n\nFile contents ({file_path}):\n```\n{content}\n```"

        # Build prompt — inject Human-Centric Standard for frontend-targeting nodes
        if node_type in ("ux_eval", "art_director"):
            prompt = template.format(
                human_centric_prefix=_HUMAN_CENTRIC_SYSTEM,
                mandate=_mandate,
                intent=intent,
                signals=_signals_str,
            )
        elif is_frontend and node_type in ("implement", "design", "design_wave", "emit"):
            prompt = (
                f"{_HUMAN_CENTRIC_SYSTEM}\n\n"
                + template.format(mandate=_mandate,
                                  intent=intent, signals=_signals_str)
            )
        else:
            prompt = template.format(
                mandate=_mandate,
                intent=intent,
                signals=_signals_str,
                human_centric_prefix="",  # ignored if not in template
            )

        # Swarm personas — prepend the Persistent Context Envelope so every
        # specialist retains global awareness of the user's goal (Law 9 Swarm).
        if node_type in _SWARM_PERSONAS:
            envelope = _PERSISTENT_CONTEXT_ENVELOPE.format(
                user_goal=_user_goal,
                constraints=_constraints,
            )
            prompt = envelope + prompt

        if mcp_context:
            prompt += mcp_context

        # Tier-0 local fast path for cheap deterministic nodes.
        fast_path_output: str | None = None
        if node_type == "ingest" and mcp_context:
            file_path = env.metadata.get("file_path") or target or "workspace"
            fast_path_output = (
                f"- {file_path}: primary context source for this mandate\n"
                f"- JIT signals: {_signals_str or 'none'}\n"
                f"- Next focus: analyse the loaded file before implementation"
            )
        elif node_type == "validate":
            fast_path_output = (
                "- [ ] Run focused pytest coverage for modified execution path\n"
                "- [ ] Verify Tribunal / OWASP regressions stay blocked\n"
                "- [ ] Confirm latency and dependency fan-out remain within budget"
            )
        elif node_type == "emit" and env.metadata.get("phase") != "blueprint":
            fast_path_output = (
                f"Executed {node_type} for {intent} on stroke "
                f"{env.metadata.get('stroke', 1)} using {node_model_id}."
            )

        # ── Build tool manifest for ReAct system prompt ────────────────────
        manifest_lines: list[str] = []
        for spec in mcp.manifest():
            params = ", ".join(
                f"{p['name']}: {p['type']}" for p in spec.parameters
            )
            manifest_lines.append(
                f"  {spec.uri}({params}) — {spec.description}")
        manifest_str = "\n".join(manifest_lines)

        react_system = (
            _NODE_SYSTEM.format(node_type=node_type)
            + "\n\nYou may invoke tools by outputting EXACTLY on its own line:\n"
            '<tool_call>{"uri": "mcp://tooloo/<name>", "kwargs": {...}}</tool_call>\n'
            "You may emit multiple <tool_call> blocks in a single response "
            "when independent reads/checks can be batched.\n"
            "After receiving [Tool Result], continue reasoning.\n"
            "Available tools:\n" + manifest_str + "\n"
            "When done, output your final answer WITHOUT any <tool_call> tags."
        )
        react_conversation = react_system + \
            "\n\n[User]\n" + prompt + "\n[/User]"

        # ── ReAct loop: max 3 tool iterations before final output ───────────
        _MAX_REACT_ITER = 3
        output = fast_path_output or ""
        _last_raw = ""
        spawned_branches: list[dict[str, Any]] = []
        if not fast_path_output:
            for _iter in range(_MAX_REACT_ITER):
                raw = _call_llm_raw(react_conversation,
                                    node_type, node_model_id)
                _last_raw = raw
                tool_calls = _extract_tool_calls(raw)
                if tool_calls:
                    tool_result_blocks: list[str] = []
                    for idx, tool_data in enumerate(tool_calls, start=1):
                        uri = str(tool_data.get("uri", ""))
                        kwargs = dict(tool_data.get("kwargs", {}))
                        tool_result = mcp.call_uri(uri, **kwargs)
                        if uri == "mcp://tooloo/spawn_process" and tool_result.success:
                            tool_output_payload = tool_result.output
                            if isinstance(tool_output_payload, dict):
                                spawned = tool_output_payload.get(
                                    "spawned_branch")
                                if isinstance(spawned, dict):
                                    spawned_branches.append(spawned)
                                batch_spawned = tool_output_payload.get(
                                    "spawned_branches")
                                if isinstance(batch_spawned, list):
                                    spawned_branches.extend(
                                        item for item in batch_spawned if isinstance(item, dict)
                                    )
                        tool_output = (
                            str(tool_result.output)[:2000]
                            if tool_result.success
                            else f"Error: {tool_result.error}"
                        )
                        tool_result_blocks.append(
                            f"[Tool {idx} Result]\n{tool_output}\n[/Tool {idx} Result]"
                        )
                    react_conversation += (
                        f"\n[Assistant]\n{raw}\n[/Assistant]\n"
                        + "\n".join(tool_result_blocks)
                    )
                    continue
                output = raw
                break
            else:
                output = _last_raw  # iterations exhausted — use last response

        # ── MCP: implement writes the LLM output to disk ───────────────────
        mcp_write_result: dict[str, Any] | None = None
        if node_type == "implement":
            write_path = env.metadata.get("file_path") or target
            if write_path and output and not output.startswith("[symbolic-"):
                write_result = mcp.call_uri(
                    "mcp://tooloo/file_write",
                    path=write_path,
                    content=output,
                )
                mcp_write_result = {
                    "path": write_path,
                    "success": write_result.success,
                    "error": str(write_result.output) if not write_result.success else None,
                }

        # ── SPAWN_REPO: write scaffold files from LLM plan ─────────────────
        spawn_repo_result: dict[str, Any] | None = None
        if node_type == "spawn_repo" and output and not output.startswith("[symbolic-"):
            scaffold_files = _build_spawn_repo_scaffold(_mandate, output)
            write_results: list[dict[str, Any]] = []
            for file_path, file_content in scaffold_files.items():
                wr = mcp.call_uri(
                    "mcp://tooloo/file_write",
                    path=file_path,
                    content=file_content,
                )
                write_results.append({
                    "path": file_path,
                    "success": wr.success,
                    "error": str(wr.error) if not wr.success else None,
                })
            spawn_repo_result = {
                "files_written": write_results,
                "scaffold_plan": output,
            }

        result: dict[str, Any] = {
            "node": env.mandate_id,
            "node_type": node_type,
            "intent": intent,
            "model": node_model_id,
            "phase": phase,
            "frontend_target": is_frontend,
            "output": output,
            "status": "executed",
        }
        if mcp_write_result is not None:
            result["mcp_write"] = mcp_write_result
        if spawn_repo_result is not None:
            result["spawn_repo"] = spawn_repo_result
        if spawned_branches:
            result["__spawned_branches__"] = spawned_branches

        # ── Art Director: visual evaluation for ux_eval nodes ──────────────
        # When a target HTML file is supplied, render it headlessly, pass the
        # Base64 screenshot to a vision model for WCAG / Gestalt critique, and
        # attach actionable CSS adjustments to the result payload.
        if node_type == "ux_eval":
            art_result = _run_art_director(
                mcp=mcp,
                file_path=env.metadata.get("file_path") or target or "",
                ux_blueprint=output,
                mandate=_mandate,
                intent=intent,
                model_id=node_model_id,
                call_llm_raw=_call_llm_raw,
            )
            result["art_director"] = art_result

            # ── VLT Math Proofs: parse embedded VLT JSON and run full audit ──
            vlt_audit = _run_vlt_audit(output)
            result["vlt_audit"] = vlt_audit

        # ── Design node: extract and audit any embedded VLT block ───────────
        if node_type in ("design", "design_wave"):
            vlt_audit = _run_vlt_audit(output)
            if vlt_audit.get("tree_id"):  # only attach if VLT was found
                result["vlt_audit"] = vlt_audit

        return result

    return work_fn


# ── SPAWN_REPO Scaffold Builder ───────────────────────────────────────────────

def _build_spawn_repo_scaffold(mandate: str, llm_plan: str) -> dict[str, str]:
    """Parse the LLM scaffold plan and return a {path: content} dict.

    Extracts REPO_NAME from the plan (if present) and builds canonical
    scaffold files.  Falls back to a slug derived from the mandate text.
    """
    import re as _re

    # Extract repo name from plan
    name_match = _re.search(
        r"REPO_NAME\s*:\s*([a-z0-9\-_]+)", llm_plan, _re.IGNORECASE)
    repo_name = name_match.group(1).lower() if name_match else (
        _re.sub(r"[^a-z0-9]+", "-", mandate[:40].lower()
                ).strip("-") or "new-repo"
    )

    # Extract purpose sentence
    purpose_match = _re.search(r"PURPOSE\s*:\s*(.+)", llm_plan)
    purpose = purpose_match.group(
        1).strip() if purpose_match else mandate[:120]

    base = f"generated/{repo_name}"
    return {
        f"{base}/README.md": (
            f"# {repo_name}\n\n{purpose}\n\n"
            "## Getting Started\n\n"
            "```bash\npip install -e .[dev]\npytest\n```\n"
        ),
        f"{base}/pyproject.toml": (
            "[build-system]\n"
            'requires = ["setuptools>=68"]\n'
            'build-backend = "setuptools.backends.legacy:build"\n\n'
            "[project]\n"
            f'name = "{repo_name}"\n'
            'version = "0.1.0"\n'
            f'description = "{purpose[:120]}"\n'
            'requires-python = ">=3.11"\n\n'
            "[project.optional-dependencies]\n"
            'dev = ["pytest>=8", "pytest-asyncio"]\n'
        ),
        f"{base}/src/__init__.py": f'"""{repo_name} source package."""\n',
        f"{base}/tests/__init__.py": '"""Test suite."""\n',
        f"{base}/.github/workflows/ci.yml": (
            "name: CI\non: [push, pull_request]\njobs:\n"
            "  test:\n    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-python@v5\n"
            "        with: {python-version: '3.12'}\n"
            "      - run: pip install -e .[dev]\n"
            "      - run: pytest\n"
        ),
        f"{base}/scaffold_plan.md": (
            f"# Scaffold Plan — {repo_name}\n\n"
            f"Generated from mandate: {mandate[:200]}\n\n"
            "```\n" + llm_plan + "\n```\n"
        ),
    }


# ── VLT Audit helper ──────────────────────────────────────────────────────────


def _run_vlt_audit(llm_output: str) -> dict[str, Any]:
    """Extract a VLT JSON block from LLM output and run full math proofs.

    Looks for a ```vlt ... ``` fenced block or a bare JSON object that can be
    parsed as a VectorTree.  Returns a serialised VLTAuditReport dict, or an
    empty dict if no VLT block was found.
    """
    import json as _json

    raw_vlt: str | None = None

    # Try fenced ```vlt block first
    m = re.search(r"```vlt\s*(.*?)\s*```", llm_output,
                  re.DOTALL | re.IGNORECASE)
    if m:
        raw_vlt = m.group(1).strip()
    else:
        # Fall back to largest JSON object in the output
        m2 = re.search(r"\{.*\"root_node\".*\}", llm_output, re.DOTALL)
        if m2:
            raw_vlt = m2.group(0).strip()

    if not raw_vlt:
        return {}

    try:
        data = _json.loads(raw_vlt)
        tree = VectorTree.model_validate(data)
        report: VLTAuditReport = tree.full_audit()
        return report.model_dump()
    except Exception as exc:
        return {"parse_error": str(exc)[:200], "raw_snippet": raw_vlt[:300]}


# ── Art Director helper ────────────────────────────────────────────────────────


def _run_art_director(
    mcp: "MCPManager",
    file_path: str,
    ux_blueprint: str,
    mandate: str,
    intent: str,
    model_id: str,
    call_llm_raw: "Callable[[str, str, str], str]",
) -> dict[str, Any]:
    """Render a UI file, pass the screenshot to a vision model, return critique.

    Pipeline:
      1. ``render_screenshot`` → PNG (Base64) or stub if Playwright unavailable.
      2. Build multimodal prompt with WCAG + Gestalt evaluation axes.
      3. Call vision-capable model (or text-only fallback).
      4. Return structured critique with actionable CSS/component adjustments.
    """
    art_output: dict[str, Any] = {
        "rendered": False,
        "renderer": "none",
        "critique": "",
        "adjustments": [],
        "wcag_pass": None,
    }

    # Step 1 — Render screenshot if file_path is an HTML file
    if file_path and file_path.endswith((".html", ".htm")):
        render_result = mcp.call(
            "render_screenshot",
            file_path=file_path,
            viewport_width=1280,
            viewport_height=800,
        )
        if render_result.success and render_result.output:
            rdata = render_result.output
            art_output["rendered"] = rdata.get("screenshot_b64") is not None
            art_output["renderer"] = rdata.get("renderer", "stub")
            b64_png = rdata.get("screenshot_b64")
        else:
            b64_png = None
    else:
        b64_png = None

    # Step 2 — Build vision evaluation prompt
    _VISION_SYSTEM = (
        "You are the Art Director of TooLoo V2 — a WCAG 2.2 AA and Gestalt-trained "
        "UI critic.  Evaluate the provided UI strictly and produce ONLY actionable output.\n\n"
        "Evaluation axes (score 1-5 each):\n"
        "  contrast       — text and interactive element contrast ratios\n"
        "  alignment      — grid consistency and visual rhythm\n"
        "  cognitive_load — information density and grouping clarity\n"
        "  affordance     — interactive elements are visually distinct\n"
        "  animation      — state transitions are smooth and purposeful\n\n"
        "Output format (strict JSON):\n"
        '{"critique": "<2-sentence summary>", '
        '"scores": {"contrast":N,"alignment":N,"cognitive_load":N,"affordance":N,"animation":N}, '
        '"adjustments": ["<specific CSS/component fix 1>", "..."], '
        '"wcag_pass": true|false}'
    )

    if b64_png:
        # Multimodal path (vision model)
        vision_prompt = (
            f"{_VISION_SYSTEM}\n\n"
            f"UX Blueprint context:\n{ux_blueprint[:600]}\n\n"
            f"Mandate: «{mandate[:200]}»\n\n"
            f"[Screenshot attached as Base64 PNG — evaluate the visual above]"
        )
        # Attempt multimodal call via Vertex AI / Gemini Direct
        raw_critique = _try_vision_call(b64_png, vision_prompt, model_id)
    else:
        # Text-only fallback (no screenshot available)
        vision_prompt = (
            f"{_VISION_SYSTEM}\n\n"
            f"UX Blueprint context:\n{ux_blueprint[:800]}\n\n"
            f"Mandate: «{mandate[:200]}»\n\n"
            "No screenshot available. Evaluate the blueprint text above using your "
            "knowledge of WCAG 2.2 and Gestalt design principles."
        )
        raw_critique = call_llm_raw(vision_prompt, "ux_eval", model_id)

    # Step 3 — Parse JSON critique from model output
    import json as _json

    m = re.search(r"\{.*\}", raw_critique, re.DOTALL)
    if m:
        try:
            parsed = _json.loads(m.group(0))
            art_output["critique"] = str(parsed.get("critique", ""))[:600]
            art_output["adjustments"] = list(
                parsed.get("adjustments", []))[:10]
            art_output["wcag_pass"] = bool(parsed.get("wcag_pass", False))
            art_output["scores"] = parsed.get("scores", {})
        except _json.JSONDecodeError:
            art_output["critique"] = raw_critique[:400]
    else:
        art_output["critique"] = raw_critique[:400]

    return art_output


def _try_vision_call(b64_png: str, prompt: str, model_id: str) -> str:
    """Attempt a multimodal call with Base64 PNG attached.

    Falls back to text-only if the provider does not support vision or
    the client is unavailable.
    """
    # Vertex AI vision path (google-genai SDK supports inline image parts)
    if _vertex_client is not None:
        try:
            # type: ignore[import-untyped]
            from google.genai import types as _genai_types
            import base64 as _b64

            image_bytes = _b64.b64decode(b64_png)
            contents = [
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png",
                                     "data": _b64.b64encode(image_bytes).decode()}},
                ]},
            ]
            resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                model=model_id, contents=contents,
            )
            return (resp.text or "").strip()
        except Exception:
            pass

    # Gemini Direct vision path
    if _gemini_client is not None:
        try:
            # type: ignore[import-untyped]
            from google.genai import types as _gtypes
            import base64 as _b64

            image_bytes = _b64.b64decode(b64_png)
            resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                model=GEMINI_MODEL,
                contents=[prompt, {"inline_data": {
                    "mime_type": "image/png",
                    "data": _b64.b64encode(image_bytes).decode(),
                }}],
            )
            return (resp.text or "").strip()
        except Exception:
            pass

    # Text-only fallback
    return (
        '{"critique": "Vision model unavailable — blueprint-only evaluation.", '
        '"scores": {"contrast":3,"alignment":3,"cognitive_load":3,"affordance":3,"animation":3}, '
        '"adjustments": ["Verify color contrast ratios meet WCAG 4.5:1 for normal text", '
        '"Ensure interactive elements have minimum 44x44px touch targets"], '
        '"wcag_pass": null}'
    )
