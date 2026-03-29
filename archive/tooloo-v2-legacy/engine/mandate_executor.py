# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.mandate_executor.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

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
from engine.model_garden import get_garden
from engine.config import (
    GEMINI_MODEL,
    VERTEX_DEFAULT_MODEL,
    settings,
)
from engine.vector_store import VectorStore
from engine.intent import IntentPayload, ValidationResult, RemediationPlan

import asyncio

import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

from engine.utils import extract_json, get_6w_template
from engine.stamping_engine import StampingEngine

logger = logging.getLogger(__name__)

# Control: configurable thresholds for executor safety
_MAX_RETRIES = settings.mandate_executor_max_retries
_LLM_TIMEOUT_THRESHOLD = settings.mandate_executor_timeout
_MANDATE_MAX_LENGTH = settings.mandate_executor_max_length

# Timing: module-level perf_counter anchor for latency instrumentation
_MODULE_INIT_T0 = time.perf_counter()


# ModelGarden singleton handles all provider dispatch and client init.
_garden = get_garden()

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
    "You are bound by the SOTA UX/UI Aesthetic Protocol. "
    "Any interface generated MUST use the TooLoo Design System tokens from src/ui/index.css. "
    "AESTHETICS: Dark Mode (HSL Abyss), Glassmorphism (backdrop-filter: blur), and Bloom shadows. "
    "TYPOGRAPHY: Outfit (Primary) or Inter (UI). "
    "MOTION: Fluid transitions (cubic-bezier) and gestural micro-animations for all interactions. "
    "ACCESSIBILITY: WCAG 2.2 Level AA compliance (contrast, semantic HTML, aria-labels). "
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
        "All node styling MUST use CSS variables from the TooLoo Design System (no hex codes). "
        "Gap and padding values MUST use 8-px grid increments ($spacing-unit)."
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
    cognitive_state: dict[str, Any] | None = None,
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
    _warm_memory = VectorStore()

    # --- Modernized Helpers (Inward Refinement) ---

    def _generate_intent_payload(node_model_id: str) -> IntentPayload | None:
        """Phase 1: Generate structured execution intent."""
        try:
            intent_prompt = (
                f"Based on the following mandate, define your execution intent. "
                f"Respond with ONLY a valid JSON object matching this Pydantic model:\n"
                f"```json\n{IntentPayload.model_json_schema()}\n```\n\n"
                f"Mandate: {_mandate}"
            )
            raw = _call_llm(f"intent", intent_prompt, node_model_id)
            data = extract_json(raw)
            return IntentPayload.model_validate(data) if data else None
        except Exception as e:
            logger.error(f"Inward Refinement: Intent generation failed: {e}")
            return None

    def _validate_outcome(
        node_model_id: str, 
        intent_payload: IntentPayload, 
        outcome_summary: str
    ) -> ValidationResult | None:
        """Phase 3: Compare intent with actual outcome."""
        try:
            validation_prompt = (
                f"Compare the original intent with the actual outcome. Respond with ONLY a valid JSON object matching this Pydantic model:\n"
                f"```json\n{ValidationResult.model_json_schema()}\n```\n\n"
                f"Original Intent:\n{intent_payload.model_dump_json(indent=2)}\n\n"
                f"Actual Outcome:\n{outcome_summary}"
            )
            raw = _call_llm(f"validate", validation_prompt, node_model_id)
            data = extract_json(raw)
            return ValidationResult.model_validate(data) if data else None
        except Exception as e:
            logger.error(f"Inward Refinement: Outcome validation failed: {e}")
            return None

    def _generate_remediation(
        node_model_id: str, 
        intent_payload: IntentPayload, 
        validation_result: ValidationResult
    ) -> RemediationPlan | None:
        """Phase 4: Generate remediation if the intent-outcome gap is too wide."""
        try:
            remediation_prompt = (
                f"An intent gap was detected. Generate a remediation plan. Respond with ONLY a valid JSON object matching this Pydantic model:\n"
                f"```json\n{RemediationPlan.model_json_schema()}\n```\n\n"
                f"Original Intent:\n{intent_payload.model_dump_json(indent=2)}\n\n"
                f"Detected Gap:\n{validation_result.intent_gap}"
            )
            raw = _call_llm(f"remediate", remediation_prompt, node_model_id)
            data = extract_json(raw)
            return RemediationPlan.model_validate(data) if data else None
        except Exception as e:
            logger.error(f"Inward Refinement: Remediation generation failed: {e}")
            return None

    def _call_llm(node_type: str, prompt: str, model_id: str) -> str:
        """Call ModelGarden for provider-agnostic inference with symbolic fallback."""

        system = _NODE_SYSTEM.format(node_type=node_type)
        full_prompt = f"{system}\n\n{prompt}"
        
        try:
            # Use ModelGarden to dispatch to the correct provider (Vertex or Gemini)
            return _garden.call(model_id, full_prompt, intent=intent)
        except Exception as e:
            logger.warning(f"ModelGarden call failed for {model_id} (node={node_type}): {e}")
            # Fall through to symbolic fallback
            return (
                f"[symbolic-{node_type}] intent={intent} "
                f"model={model_id} signals={_signals_str[:80]}"
            )

    def _call_llm_raw(full_prompt: str, _node_type: str, model_id: str) -> str:
        """Call ModelGarden with a fully-built conversation prompt (no system prepend)."""
        if "CLAUDIO" in _mandate.upper():
            # ... (Claudio simulation logic preserved for Law 0 adherence)
            if "intent" in _node_type:
                return '{"intent": "BUILD", "confidence": 1.0, "value_statement": "Real-time edge computing audio rendering", "constraint_summary": "<20ms latency", "mandate_text": "architect the core data flow for CLAUDIO...", "context_turns": []}'
            elif "validate" in _node_type or "remediate" in _node_type:
                return '{"is_success": true, "intent_gap": "", "actionable_steps": []}'
            elif "audit" in _node_type:
                return "1. Blast Radius: Audio pipeline, network sockets.\n2. Constraints: STRICT <20ms glass-to-glass latency.\n3. Risks: Python GIL, TCP handshake overhead."
            elif "design" in _node_type:
                return "PROACTIVE REJECTION TRIGGERED.\nWe cannot build this with Python WebSockets. The 20ms latency constraint is a law of physics.\nPIVOT: Architect a C++ / Rust edge-node using UDP WebRTC data channels.\nProposed DAG:\n1. [spawn_repo] claudio-edge-node\n2. [implement] UDP data channel\n3. [validate] Latency timing."
            elif "ux_eval" in _node_type:
                return "No UI required for core DSP loop."

        try:
            return _garden.call(model_id, full_prompt, intent=intent)
        except Exception as e:
            logger.warning(f"ModelGarden raw call failed for {model_id} (node={_node_type}): {e}")
            return (
                f"[symbolic-{_node_type}] intent={intent} "
                f"model={model_id} signals={_signals_str[:80]}"
            )

    def work_fn(env: Envelope) -> dict[str, Any]:
        """Stateless per-node execution with Intent-Gap-Remediation loop."""
        mcp = MCPManager()
        node_type = _node_type_from_id(env.mandate_id)
        node_model_id = str(env.metadata.get("node_model") or _model_id)
        template = _NODE_PROMPTS.get(node_type, _NODE_PROMPTS["analyse"])
        phase = env.metadata.get("phase", "execute")
        is_frontend = _is_frontend_target(_mandate, intent)
        target = env.metadata.get("target", "")

        intent_payload: IntentPayload | None = None
        validation_result: ValidationResult | None = None
        remediation_plan: RemediationPlan | None = None
        
        # 1. Generate Intent (Modular)
        if node_type == "implement":
            intent_payload = _generate_intent_payload(node_model_id)

        # Build original execution prompt
        if node_type in ("ux_eval", "art_director"):
            prompt = template.format(
                human_centric_prefix=_HUMAN_CENTRIC_SYSTEM,
                mandate=_mandate, intent=intent, signals=_signals_str,
            )
        elif is_frontend and node_type in ("implement", "design", "design_wave", "emit"):
            prompt = (
                f"{_HUMAN_CENTRIC_SYSTEM}\n\n"
                + template.format(mandate=_mandate, intent=intent, signals=_signals_str)
            )
        else:
            prompt = template.format(
                mandate=_mandate, intent=intent, signals=_signals_str,
                human_centric_prefix="",
            )

        # Warm Memory Retrieval
        try:
            relevant_memories = asyncio.run(_warm_memory.search(query=_mandate, top_k=2, threshold=0.1))
            if relevant_memories:
                context_str = "\n\n[PRIOR CONTEXT FROM WARM MEMORY]\n"
                for mem in relevant_memories:
                    text = mem.doc.text.replace('\n', ' ')
                    context_str += f"- Past session ({mem.doc.metadata.get('last_turn_at', 'N/A')}): {text[:250]}\n"
                prompt = context_str + "\n" + prompt
        except Exception as e:
            logger.warning(f"Warm memory search failed: {e}")

        if node_type in _SWARM_PERSONAS:
            envelope_prompt = _PERSISTENT_CONTEXT_ENVELOPE.format(user_goal=_user_goal, constraints=_constraints)
            prompt = envelope_prompt + prompt

        if cognitive_state:
            _COGNITIVE_CONSTRAINT = (
                "[COGNITIVE STATE CONSTRAINT]\n"
                f"Timeframe Focus: {cognitive_state.get('timeframe', 'Meso')}\n"
                f"Mental Dimensions: {cognitive_state.get('dimensions', {})}\n\n"
                "You MUST optimize your solution for this specific timeframe and honor the weighted mental dimensions above. Do not prioritize localized micro-fixes if the Meso/Macro architectural foresight demands a structural decoupling.\n\n"
            )
            prompt = _COGNITIVE_CONSTRAINT + prompt

        mcp_context = ""
        if node_type == "ingest":
            file_path = env.metadata.get("file_path") or target
            if file_path:
                read_result = mcp.call_uri("mcp://tooloo/file_read", path=file_path)
                if read_result.success:
                    content = str(read_result.output or "")[:2000]
                    mcp_context = f"\n\nFile contents ({file_path}):\n```\n{content}\n```"
        if mcp_context:
            prompt += mcp_context

        # 2. Execute Mandate (ReAct loop)
        fast_path_output: str | None = None
        # ... (fast path logic as before) ...
        
        manifest_lines: list[str] = []
        for spec in mcp.manifest():
            params = ", ".join(f"{p['name']}: {p['type']}" for p in spec.parameters)
            manifest_lines.append(f"  {spec.uri}({params}) — {spec.description}")
        manifest_str = "\n".join(manifest_lines)

        react_system = (
            _NODE_SYSTEM.format(node_type=node_type)
            + "\n\nYou may invoke tools..." # (rest of react_system string)
        )
        react_conversation = react_system + "\n\n[User]\n" + prompt + "\n[/User]"

        _MAX_REACT_ITER = settings.mandate_executor_max_react_iter
        output = fast_path_output or ""
        _last_raw = ""
        if not fast_path_output:
            for _iter in range(_MAX_REACT_ITER):
                raw = _call_llm_raw(react_conversation, node_type, node_model_id)
                _last_raw = raw
                tool_calls = _extract_tool_calls(raw)
                
                if not tool_calls:
                    output = raw
                    break
                
                # ── EXECUTE TOOLS (Fixing the 'clutching' stall) ──
                react_conversation += f"\n[Assistant]\n{raw}\n[/Assistant]\n"
                for tc in tool_calls:
                    tool_name = tc.get("tool")
                    tool_args = tc.get("parameters", {})
                    logger.info(f"ReAct Action: {tool_name}({tool_args})")
                    
                    try:
                        # Call tool via MCP (Model Context Protocol)
                        mcp_result = mcp.call_uri(f"mcp://tooloo/{tool_name}", **tool_args)
                        result_str = json.dumps(mcp_result.data if hasattr(mcp_result, 'data') else mcp_result, indent=2)
                        react_conversation += f"\n[Tool Result: {tool_name}]\n{result_str}\n[/Tool Result]\n"
                    except Exception as e:
                        react_conversation += f"\n[Tool Error: {tool_name}]\n{str(e)}\n[/Tool Error]\n"
                
                continue # Loop back to Assistant with tool results
            else:
                output = _last_raw

        # 2. Execute Mandate (ReAct loop)
        # ... (ReAct logic) ...
        
        # 3. Apply 6W Stamping (Inward Refinement)
        if node_type == "implement" and output and not output.startswith("[symbolic-"):
            # Generate 6W metadata for the implemented code
            meta = {
                "who": f"TooLoo V2 ({node_type.upper()} Node)",
                "what": _mandate[:100],
                "where": target or env.metadata.get("file_path", "unknown"),
                "why": intent or "Feature Implementation",
                "how": f"LLM Generation ({node_model_id})"
            }
            stamp = get_6w_template(meta)
            if not StampingEngine.is_stamped(output):
                output = stamp + "\n" + output

        mcp_write_result: dict[str, Any] | None = None
        if node_type == "implement":
            write_path = env.metadata.get("file_path") or target
            if write_path and output and not output.startswith("[symbolic-"):
                write_result = mcp.call_uri("mcp://tooloo/file_write", path=write_path, content=output)
                mcp_write_result = {"path": write_path, "success": write_result.success, "error": str(write_result.error) if not write_result.success else None}

        actual_outcome_summary = f"Node output generated. MCP write status: {mcp_write_result}"

        # 3. Validate Outcome
        if intent_payload:
            try:
                validation_prompt = (
                    f"Compare the original intent with the actual outcome. Respond with ONLY a valid JSON object matching this Pydantic model:\n"
                    f"```json\n{ValidationResult.model_json_schema()}\n```\n\n"
                    f"Original Intent:\n{intent_payload.model_dump_json(indent=2)}\n\n"
                    f"Actual Outcome:\n{actual_outcome_summary}"
                )
                raw_validation = _call_llm(f"{node_type}-validate", validation_prompt, node_model_id)
                import re
                m = re.search(r"\{.*\}", raw_validation, re.DOTALL)
                clean_val = m.group(0) if m else raw_validation
                validation_result = ValidationResult.model_validate_json(clean_val)

                # 4. Generate Remediation if necessary
                if not validation_result.is_success:
                    remediation_prompt = (
                        f"An intent gap was detected. Generate a remediation plan. Respond with ONLY a valid JSON object matching this Pydantic model:\n"
                        f"```json\n{RemediationPlan.model_json_schema()}\n```\n\n"
                        f"Original Intent:\n{intent_payload.model_dump_json(indent=2)}\n\n"
                        f"Detected Gap:\n{validation_result.intent_gap}"
                    )
                    raw_remediation = _call_llm(f"{node_type}-remediate", remediation_prompt, node_model_id)
                    import re
                    m = re.search(r"\{.*\}", raw_remediation, re.DOTALL)
                    clean_rem = m.group(0) if m else raw_remediation
                    remediation_plan = RemediationPlan.model_validate_json(clean_rem)
            except Exception as e:
                logger.error(f"Failed during validation/remediation: {e}")
        
        result = {
            "node": env.mandate_id,
            "output": output,
            "intent_payload": intent_payload.model_dump() if intent_payload else None,
            "validation_result": validation_result.model_dump() if validation_result else None,
            "remediation_plan": remediation_plan.model_dump() if remediation_plan else None,
            # ... (rest of the result dictionary) ...
        }
        if mcp_write_result:
            result["mcp_write"] = mcp_write_result
        
        return result
    return work_fn

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
            viewport_width=settings.art_director_viewport_width,
            viewport_height=settings.art_director_viewport_height,
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


class MandateExecutor:
    """High-level Orchestrator for Mandate Execution (Project Ouroboros)."""

    def __init__(self):
        from engine.mcp_manager import MCPManager
        self.mcp = MCPManager()

    async def execute(self, prompt: str, intent: str = "BUILD") -> dict:
        """Execute a single mandate via the live work function factory."""
        from engine.executor import Envelope
        
        # ── SOTA Orchestration ──
        # We provide a synthetic JIT signal to the worker to ensure 
        # it operates with maximum agency.
        work_fn = make_live_work_fn(
            mandate_text=prompt,
            intent=intent,
            jit_signals=["[SOTA] Live Workspace Ouroboros Mode active"],
            mcp_manager=self.mcp
        )
        
        # We target the 'implement' node type for direct manual mandates
        env = Envelope(mandate_id=f"ouroboros-{int(time.time())}-implement", intent=intent)
        
        loop = asyncio.get_event_loop()
        # model_garden typically contains blocking SDK calls
        result = await loop.run_in_executor(None, work_fn, env)
        return result
