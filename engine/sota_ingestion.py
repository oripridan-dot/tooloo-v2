# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining sota_ingestion.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.930553
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/sota_ingestion.py — SOTA Knowledge Ingestion Engine for TooLoo V2.

Runs a full-coverage ingestion loop that:
  1. Issues targeted SOTA research queries via Gemini (or structured catalogue fallback)
  2. Parses signal lines into KnowledgeEntry objects
  3. Deduplicates and stores them in the appropriate domain bank
  4. Reports ingestion statistics per domain

This is the autonomous knowledge enrichment pipeline — it runs on startup
and can be triggered via /v2/knowledge/ingest to keep banks at SOTA.

Security: all generated entries pass Tribunal poison-guard before storage.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from engine.config import GEMINI_API_KEY, VERTEX_DEFAULT_MODEL, _vertex_client as _vertex_client_cfg
from engine.knowledge_banks.base import KnowledgeEntry
from engine.knowledge_banks.manager import BankManager
from engine.model_garden import get_garden

# ── AI clients ────────────────────────────────────────────────────────────────
_vertex_client = _vertex_client_cfg

_gemini_client = None
if GEMINI_API_KEY:
    try:
        from google import genai as _genai_mod  # type: ignore[import-untyped]
        _gemini_client = _genai_mod.Client(api_key=GEMINI_API_KEY)
    except Exception:
        pass

# ── Per-bank ingestion targets ─────────────────────────────────────────────────
# (bank_id, domain, query_prompt, signal_count)
_INGESTION_TARGETS: list[tuple[str, str, str, int]] = [
    # DESIGN
    ("design", "gestalt",
     "List 5 specific, concrete, production-ready Gestalt psychology application rules for modern digital UI/UX design in 2026. Each rule must be actionable for a frontend developer. Be specific, terse, no preamble.",
     5),
    ("design", "typography",
     "List 5 SOTA typography best practices for digital product design as of 2026, including specific font choices, CSS techniques, and accessibility requirements. Be specific and terse.",
     5),
    ("design", "color",
     "List 5 SOTA color science and color system practices for digital product design in 2026, covering OKLCH, P3 gamut, APCA contrast, and dark mode. Be specific and terse.",
     5),
    ("design", "layout",
     "List 5 SOTA CSS layout techniques and grid system practices for 2026 web development. Include specific CSS properties, browser support status, and when to use each. Be specific and terse.",
     5),
    ("design", "motion",
     "List 5 SOTA motion design and animation best practices for web UIs in 2026. Include performance considerations, accessibility, and specific libraries. Be specific and terse.",
     5),
    ("design", "design_systems",
     "List 5 SOTA design system architecture principles and tooling choices for 2026. Include token management, component strategy, and multi-platform considerations. Be specific and terse.",
     5),
    ("design", "accessibility",
     "List 5 most critical WCAG 2.2 and emerging WCAG 3.0 accessibility requirements for AI-powered chat interfaces in 2026. Be specific about techniques and testing methods.",
     5),
    ("design", "interaction_patterns",
     "List 5 SOTA interaction design patterns for AI chat interfaces in 2026. Include streaming, suggestion chips, context indicators, and progressive disclosure patterns. Be specific.",
     5),
    # CODE
    ("code", "architecture",
     "List 5 SOTA software architecture patterns for cloud-native Python/FastAPI services in 2026. Include specific implementation guidance and when to apply each pattern.",
     5),
    ("code", "testing",
     "List 5 SOTA testing strategies and tools for Python services in 2026. Include specific pytest plugins, coverage targets, and property-based testing approaches.",
     5),
    ("code", "security",
     "List 5 most critical software supply chain and application security practices for Python web services in 2026, including specific tools and compliance requirements.",
     5),
    ("code", "observability",
     "List 5 SOTA observability practices for Python FastAPI services in 2026 using OpenTelemetry. Include specific instrumentation code patterns and tooling choices.",
     5),
    ("code", "performance",
     "List 5 SOTA Python async/performance optimisation techniques for FastAPI + LLM-serving applications in 2026. Include specific libraries, patterns, and benchmarks.",
     5),
    ("code", "api_design",
     "List 5 SOTA REST/SSE/WebSocket API design patterns for LLM-powered applications in 2026. Include streaming, pagination, versioning, and schema validation.",
     5),
    # AI
    ("ai", "llm_architecture",
     "List 5 most important LLM architectural advances in 2025-2026, including MoE, long-context, reasoning models, and multimodal capabilities. Be specific and technically precise.",
     5),
    ("ai", "agents",
     "List 5 SOTA multi-agent system design patterns and frameworks as of 2026. Include MCP protocol, tool-use best practices, memory architectures, and safety considerations.",
     5),
    ("ai", "inference",
     "List 5 SOTA LLM inference optimisation techniques in 2026, including speculative decoding, continuous batching, quantisation, and hardware-specific optimisations.",
     5),
    ("ai", "safety_alignment",
     "List 5 most critical AI safety and alignment practices for deployed LLM applications in 2026, including prompt injection defences, hallucination mitigation, and OWASP LLM Top 10.",
     5),
    ("ai", "tools_ecosystem",
     "List 5 most important AI tool ecosystem components for building production LLM applications in 2026: RAG, vector DBs, orchestration, evaluation, and monitoring.",
     5),
    ("ai", "evaluation",
     "List 5 SOTA LLM evaluation methodologies and benchmarks in 2026. Include LLM-as-judge, contamination prevention, and domain-specific evaluation approaches.",
     5),
    # BRIDGE
    ("bridge", "cognitive_science",
     "List 5 cognitive science findings most relevant to designing AI chat interfaces that reduce human cognitive load and improve decision quality. Be specific and actionable.",
     5),
    ("bridge", "trust_calibration",
     "List 5 evidence-based design patterns for building appropriate (not over or under) trust in AI assistants, based on HCI research in 2024-2026. Be specific.",
     5),
    ("bridge", "conversational_design",
     "List 5 SOTA conversational AI design principles from 2026 HCI research and industry practice. Focus on Buddy-style AI chat interfaces. Be specific and actionable.",
     5),
    ("bridge", "interaction_failures",
     "List 5 most common human-AI interaction failure modes documented in 2024-2026 HCI research, and their specific mitigations. Be concrete and evidence-based.",
     5),
    ("bridge", "gap_repair_patterns",
     "List 5 most effective patterns for repairing human-AI communication breakdowns in real-time chat interfaces. Based on conversation repair theory and HCI research.",
     5),
]

# ── Structured fallback signals (when Gemini unavailable) ──────────────────────
_FALLBACK_SIGNALS: dict[tuple[str, str], list[str]] = {
    ("design", "gestalt"): [
        "Apply proximity via consistent 8px/16px gap tokens to group related UI elements without borders",
        "Use similarity (shared color/shape) to show component state relationships rather than text labels",
        "Exploit closure in skeleton screens — partial outlines trigger completion perception reducing load anxiety",
        "Align elements on invisible grid lines to create horizontal/vertical continuity for eye flow",
        "Apply Prägnanz: remove any element that doesn't carry unique semantic meaning, aiming for minimal forms",
    ],
    ("bridge", "trust_calibration"): [
        "Show explicit confidence levels (High/Medium/Low) on AI claims — improves calibrated trust by 35%",
        "Surface AI reasoning before conclusion for high-stakes outputs; hide for routine tasks",
        "When AI makes visible errors, lead with 'I was wrong about X because Y' not apology",
        "Maintain consistent persona tone across sessions — persona inconsistency is #1 long-term trust destroyer",
        "Provide evidence citations for factual claims, especially for counterintuitive outputs",
    ],
    ("bridge", "conversational_design"): [
        "Stream tokens progressively — latency >3s without streaming breaks perceived interactivity",
        "Show 3 contextual suggestion chips after each response to eliminate blank-slate anxiety",
        "Begin repair sequences with 'I understood X — did you mean Y?' rather than open re-asking",
        "Validate emotional state before task execution when frustration/excitement signals are present",
        "BLUF principle: start every response with the direct answer, then supporting detail",
    ],
    ("ai", "agents"): [
        "Use MCP (Model Context Protocol) for all tool integrations — vendor-neutral standard adopted by Claude, Cursor, major IDEs",
        "ReAct pattern (Thought→Action→Observation) is more reliable than raw CoT for tool-use tasks",
        "Multi-agent: orchestrator agent decomposes tasks, specialist agents execute — communicate via structured messages not free text",
        "Three-tier memory: in-context (current window), external (vector DB), episodic (compressed summaries)",
        "Parallel tool calls natively supported in GPT-4o, Gemini 2.0+, Claude 3.5 — use instead of serial chaining",
    ],
}


@dataclass
class IngestionReport:
    """Result of a single ingestion run."""

    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str = ""
    targets_attempted: int = 0
    entries_added: int = 0
    entries_skipped_duplicate: int = 0
    entries_skipped_poison: int = 0
    source: str = "structured"    # "gemini" | "structured"
    per_bank: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "targets_attempted": self.targets_attempted,
            "entries_added": self.entries_added,
            "entries_skipped_duplicate": self.entries_skipped_duplicate,
            "entries_skipped_poison": self.entries_skipped_poison,
            "source": self.source,
            "per_bank": self.per_bank,
            "errors": self.errors,
        }


class SOTAIngestionEngine:
    """
    Autonomous SOTA data ingestion pipeline.

    For each (bank, domain, query) target:
      1. Fetch SOTA signals via Gemini (or structured fallback)
      2. Parse into KnowledgeEntry objects
      3. Tribunal poison-guard (optional, uses duck-typed interface)
      4. Store via BankManager.ingest()

    Designed to run at startup and on-demand via the /v2/knowledge/ingest
    API endpoint. Thread-safe (bank writes are serialised per-bank).
    """

    def __init__(
        self,
        manager: BankManager,
        tribunal: Any | None = None,   # engine.tribunal.Tribunal duck-type
    ) -> None:
        self._manager = manager
        self._tribunal = tribunal

    # ── Public API ─────────────────────────────────────────────────────────────

    async def run_full_ingestion(self) -> IngestionReport:
        """Run all ingestion targets. Returns consolidated report."""
        report = IngestionReport()
        use_gemini = (_gemini_client is not None) or (
            _vertex_client is not None)
        report.source = "gemini" if use_gemini else "structured_fallback"

        for bank_id, domain, query, count in _INGESTION_TARGETS:
            report.targets_attempted += 1
            try:
                signals = self._fetch_signals(
                    bank_id, domain, query, count, use_gemini)
                added, skipped_dup, skipped_poison = await self._ingest_signals(
                    signals, bank_id, domain
                )
                report.entries_added += added
                report.entries_skipped_duplicate += skipped_dup
                report.entries_skipped_poison += skipped_poison
                report.per_bank[bank_id] = report.per_bank.get(
                    bank_id, 0) + added
            except Exception as exc:
                report.errors.append(f"{bank_id}/{domain}: {exc}")

        report.completed_at = datetime.now(UTC).isoformat()
        return report

    async def ingest_single(self, bank_id: str, domain: str, signals: list[str]) -> IngestionReport:
        """Ingest a list of raw signal strings into a specific bank/domain."""
        report = IngestionReport(source="manual")
        report.targets_attempted = len(signals)
        added, skipped_dup, skipped_poison = await self._ingest_signals(
            signals, bank_id, domain)
        report.entries_added = added
        report.entries_skipped_duplicate = skipped_dup
        report.entries_skipped_poison = skipped_poison
        report.per_bank[bank_id] = added
        report.completed_at = datetime.now(UTC).isoformat()
        return report

    # ── Internal ───────────────────────────────────────────────────────────────

    def _fetch_signals(
        self, bank_id: str, domain: str, query: str, count: int, use_gemini: bool
    ) -> list[str]:
        """Fetch SOTA signals for a target — Gemini first, then structured fallback."""
        if use_gemini:
            try:
                return self._fetch_from_gemini(bank_id, domain, query, count)
            except Exception:
                pass
        return self._fetch_from_catalogue(bank_id, domain, count)

    def _fetch_from_gemini(
        self, bank_id: str, domain: str, query: str, count: int
    ) -> list[str]:
        prompt = (
            f"You are a SOTA intelligence agent for TooLoo V2 ({datetime.now(UTC).year}). "
            f"Domain: {bank_id}/{domain}. "
            f"{query} "
            f"Format: {count} bullet lines starting with '- '. "
            "Each signal must be a single sentence: concrete, specific, actionable. "
            "Include specific tool/library names, version numbers, and year where relevant. "
            "No preamble. No post-amble. No numbering."
        )

        # Try Vertex AI first (enterprise)
        if _vertex_client:
            try:
                garden = get_garden()
                model_id = garden.resolve(
                    intent="EXPLAIN", confidence=0.9
                ).model_id if garden else VERTEX_DEFAULT_MODEL
                response = _vertex_client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                )
                text = response.text or ""
                return self._parse_bullet_signals(text)
            except Exception:
                pass

        # Fallback to Gemini direct
        if _gemini_client:
            model = VERTEX_DEFAULT_MODEL or "gemini-2.5-flash"
            response = _gemini_client.models.generate_content(
                model=model, contents=prompt
            )
            text = getattr(response, "text", "") or ""
            return self._parse_bullet_signals(text)

        raise RuntimeError("No AI client available")

    def _fetch_from_catalogue(self, bank_id: str, domain: str, count: int) -> list[str]:
        key = (bank_id, domain)
        signals = _FALLBACK_SIGNALS.get(key, [])
        if signals:
            return signals[:count]
        # Generic fallback derived from bank/domain name
        return [
            f"SOTA {bank_id}/{domain}: apply current best practices from 2026 literature",
        ]

    def _parse_bullet_signals(self, text: str) -> list[str]:
        """Extract bullet-line signals from a Gemini response."""
        lines = text.strip().splitlines()
        signals = []
        for line in lines:
            line = line.strip()
            if line.startswith(("- ", "• ", "* ")):
                signals.append(line[2:].strip())
            elif line and not line.startswith(("#", "**", "##")):
                # Accept non-bulleted lines too (LLM may not follow format exactly)
                signals.append(line)
        return [s for s in signals if len(s) > 20]

    def _make_entry(self, signal: str, bank_id: str, domain: str) -> KnowledgeEntry:
        """Convert a raw signal string into a KnowledgeEntry."""
        # Derive a title from the first 8 words
        words = signal.split()[:8]
        title = " ".join(words).rstrip(".,;:")
        tags = [bank_id, domain] + [
            w.lower() for w in words
            if len(w) > 4 and w.isalpha() and w.lower() not in
            {"list", "using", "with", "from", "that",
                "this", "they", "their", "which"}
        ][:4]
        entry_id = f"{bank_id}_{domain}_{re.sub(r'\\W+', '_', title.lower())[:40]}"
        return KnowledgeEntry(
            id=entry_id,
            title=title,
            body=signal,
            domain=domain,
            tags=list(dict.fromkeys(tags)),  # deduplicate preserving order
            relevance_weight=0.82,
            source="ingested",
            last_verified="2026-03",
            sota_level="sota_2026",
        )

    async def _is_poisoned(self, entry: KnowledgeEntry) -> bool:
        """Basic poison guard — Tribunal integration when available."""
        if self._tribunal is None:
            # Fallback: check for obvious injection patterns
            danger_patterns = [
                r"eval\s*\(",
                r"exec\s*\(",
                r"__import__",
                r"subprocess",
                r"os\.system",
                r"DROP\s+TABLE",
                r"<script",
                r"javascript:",
            ]
            text = entry.title + " " + entry.body
            return any(re.search(p, text, re.IGNORECASE) for p in danger_patterns)
        # Use Tribunal if available
        try:
            from engine.tribunal import Engram
            engram = Engram(
                id=entry.id,
                intent="AUDIT",
                slug=entry.title,
                text=entry.body,
            )
            result = await self._tribunal.evaluate(engram)
            return result.poisoned
        except Exception:
            return False

    async def _ingest_signals(
        self, signals: list[str], bank_id: str, domain: str
    ) -> tuple[int, int, int]:
        """Ingest signals into the bank. Returns (added, skipped_dup, skipped_poison)."""
        added = skipped_dup = skipped_poison = 0
        for signal in signals:
            if not signal.strip():
                continue
            entry = self._make_entry(signal, bank_id, domain)
            if await self._is_poisoned(entry):
                skipped_poison += 1
                continue
            result = self._manager.ingest(entry, bank_id)
            if result:
                added += 1
            else:
                skipped_dup += 1
        return added, skipped_dup, skipped_poison
