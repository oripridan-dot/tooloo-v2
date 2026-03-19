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

from typing import Any, Callable

from engine.config import GEMINI_API_KEY, GEMINI_MODEL, VERTEX_DEFAULT_MODEL
from engine.config import _vertex_client as _vertex_client_cfg
from engine.executor import Envelope

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


def make_live_work_fn(
    mandate_text: str,
    intent: str,
    jit_signals: list[str],
    vertex_model_id: str | None = None,
) -> Callable[[Envelope], dict[str, Any]]:
    """Return a stateless LLM-powered work function for JITExecutor fan-out.

    Each call to the returned function is fully independent (Law 17).
    Falls back to symbolic execution when both AI clients are unavailable.

    Args:
        mandate_text:     Original mandate string (truncated to 500 chars internally).
        intent:           Routed intent (BUILD / DEBUG / AUDIT / DESIGN / …).
        jit_signals:      Up to 3 SOTA signals from JITBooster.
        vertex_model_id:  Vertex AI model ID; defaults to VERTEX_DEFAULT_MODEL.
    """
    _model_id: str = vertex_model_id or VERTEX_DEFAULT_MODEL
    _mandate: str = mandate_text[:500]
    _signals_str: str = "; ".join(jit_signals[:3]) if jit_signals else "none"

    def _call_llm(node_type: str, prompt: str) -> str:
        """Call Vertex AI → Gemini Direct → symbolic fallback."""
        system = _NODE_SYSTEM.format(node_type=node_type)
        full_prompt = f"{system}\n\n{prompt}"

        if _vertex_client is not None:
            try:
                resp = _vertex_client.models.generate_content(  # type: ignore[union-attr]
                    model=_model_id, contents=full_prompt,
                )
                text = resp.text.strip()
                if text:
                    return text
            except Exception:
                pass  # fall through to Gemini Direct

        if _gemini_client is not None:
            try:
                resp = _gemini_client.models.generate_content(  # type: ignore[union-attr]
                    model=GEMINI_MODEL, contents=full_prompt,
                )
                text = resp.text.strip()
                if text:
                    return text
            except Exception:
                pass  # fall through to symbolic

        # Symbolic fallback (offline / test mode)
        return (
            f"[symbolic-{node_type}] intent={intent} "
            f"model={_model_id} signals={_signals_str[:80]}"
        )

    def work_fn(env: Envelope) -> dict[str, Any]:
        """Stateless per-node execution — safe for parallel fan-out."""
        node_type = _node_type_from_id(env.mandate_id)
        template = _NODE_PROMPTS.get(node_type, _NODE_PROMPTS["analyse"])

        # Determine node phase from envelope metadata (injected by NStrokeEngine)
        phase = env.metadata.get("phase", "execute")
        is_frontend = _is_frontend_target(_mandate, intent)
        target = env.metadata.get("target", "")

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

        output = _call_llm(node_type, prompt)
        return {
            "node": env.mandate_id,
            "node_type": node_type,
            "intent": intent,
            "model": _model_id,
            "phase": phase,
            "frontend_target": is_frontend,
            "output": output,
            "status": "executed",
        }

    return work_fn
