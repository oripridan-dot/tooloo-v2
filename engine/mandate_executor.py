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

import json
import re
from collections.abc import Callable
from typing import Any

from engine.config import GEMINI_API_KEY, GEMINI_MODEL, VERTEX_DEFAULT_MODEL
from engine.config import _vertex_client as _vertex_client_cfg
from engine.executor import Envelope
from engine.mcp_manager import MCPManager

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

# Human-Centric Standard — prepended to all frontend node prompts
_HUMAN_CENTRIC_SYSTEM = (
    "You are bound by the Human-Centric Standard. "
    "Any interface generated must prioritize low cognitive load, clear affordances, "
    "and elegant state transitions. Code must be production-ready, utilizing smooth "
    "animations (GSAP) and clear visual hierarchy. "
    "Do not output unstyled or purely utilitarian markup. "
    "If the logic is elegant, the UI must reflect that elegance. "
    "Follow WCAG 2.2 Level AA accessibility requirements. "
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
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Produce a concrete implementation blueprint. "
        "Name the specific files, classes, and interfaces to create or modify. "
        "State the 4-wave DAG execution order. "
        "Format as numbered steps."
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
        "Output a UX Blueprint. No code yet."
    ),
    # ── Dry-run simulation node ────────────────────────────────────────────
    "dry_run": (
        "Mandate: «{mandate}»\n"
        "Intent: {intent}\n"
        "JIT SOTA signals: {signals}\n\n"
        "Phase 2 — Dry Run. Generate the exact implementation but DO NOT commit.\n"
        "Output the proposed changes as a structural diff or code block.\n"
        "Mark every change with: [STAGED] <file_path> <description>.\n"
        "Flag any concerns that would prevent promotion to execute phase."
    ),
}

# Default prompt for unrecognised node types (covers wave-index nodes)
_WAVE_NODE_PROMPTS: list[str] = [
    "audit_wave", "design_wave", "ux_eval",   # Phase 1 discovery
    "ingest", "analyse",                        # Phase 2 dry-run
    "implement", "validate", "emit",            # Phase 3 execute
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
    """
    _model_id: str = vertex_model_id or VERTEX_DEFAULT_MODEL
    _mandate: str = mandate_text[:500]
    _signals_str: str = "; ".join(jit_signals[:3]) if jit_signals else "none"
    _mcp: MCPManager = mcp_manager or MCPManager()

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
        if node_type == "ux_eval":
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
        if spawned_branches:
            result["__spawned_branches__"] = spawned_branches
        return result

    return work_fn
