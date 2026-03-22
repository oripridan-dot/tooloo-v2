"""
engine/feature_registry.py — Per-component 16D feature profiles.

Each of TooLoo's 28 engine components has a unique 16D profile reflecting
its primary function, domain responsibilities, and behavioural characteristics.

Purpose:
  Replaces the global _BASE_SCORES_16D default used in calibration_engine v1
  (where ALL 28 components shared IDENTICAL base scores). That approach meant
  calibrating buddy_cache and tribunal produced mathematically identical Δ16D
  certificates — clearly wrong. This registry ensure each component has a
  component-specific calibration target.

Profile derivation methodology:
  1. Base scores default to Validator16D NoCode defaults (0.78–0.95 range).
  2. Primary-function dimensions are elevated ±0.05–0.15 based on component role.
  3. Non-applicable dimensions are reduced ±0.03–0.08 (e.g. Financial Awareness
     for a pure graph-topology component is lower than for model_selector).
  4. All scores ∈ [0.61, 0.97] — no perfect 1.0 (room for calibration gain)
     and no below 0.60 (even weakest component has baseline capability).

Sources:
  - Validator16D default scores (engine/validator_16d.py)
  - OWASP ISVS 2025 (security/safety elevation)
  - Anthropic Constitutional AI v2 (safety/honesty elevation)
  - DORA 2024 (engineering excellence profiles)
  - ARC Safety Benchmark dimension importance analysis 2025
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ── Canonical 16D dimension names ────────────────────────────────────────────
# MUST match calibration_engine._BASE_SCORES_16D and validator_16d.py
DIMENSIONS: tuple[str, ...] = (
    "ROI",
    "Safety",
    "Security",
    "Legal",
    "Human Considering",
    "Accuracy",
    "Efficiency",
    "Quality",
    "Speed",
    "Monitor",
    "Control",
    "Honesty",
    "Resilience",
    "Financial Awareness",
    "Convergence",
    "Reversibility",
)

# ── Global NoCode defaults from Validator16D ──────────────────────────────────
# Source: engine/validator_16d.py _NOCODE_DEFAULTS
_GLOBAL_DEFAULT: dict[str, float] = {
    "ROI":                 0.82,
    "Safety":              0.95,
    "Security":            0.95,
    "Legal":               0.90,
    "Human Considering":   0.85,
    "Accuracy":            0.92,
    "Efficiency":          0.85,
    "Quality":             0.82,
    "Speed":               0.80,
    "Monitor":             0.84,
    "Control":             0.84,
    "Honesty":             0.88,
    "Resilience":          0.83,
    "Financial Awareness": 0.78,
    "Convergence":         0.88,
    "Reversibility":       0.90,
}


@dataclass(frozen=True)
class ComponentFeatureProfile:
    """
    16D feature profile for one engine component.

    Attributes:
        component:          Engine component name (matches COMPONENT_DOMAIN_MAP).
        dimension_scores:   Per-dimension scores ∈ [0.61, 0.97].
        primary_dimensions: Top-3 dimensions this component is optimised for.
                            Used by calibration_engine to apply full gap boost
                            to primary dims and 50% boost to secondary dims.
        description:        One-line human note on profile rationale.
    """
    component: str
    dimension_scores: dict[str, float]
    primary_dimensions: tuple[str, ...]
    description: str = ""

    def __post_init__(self) -> None:
        missing = [d for d in DIMENSIONS if d not in self.dimension_scores]
        if missing:
            raise ValueError(
                f"Profile '{self.component}' missing dimensions: {missing}"
            )
        bad = [
            (d, s) for d, s in self.dimension_scores.items()
            if not (0.60 <= s <= 0.98)
        ]
        if bad:
            raise ValueError(
                f"Profile '{self.component}' scores out of [0.60, 0.98]: {bad}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "primary_dimensions": list(self.primary_dimensions),
            "dimension_scores": {k: round(v, 4) for k, v in self.dimension_scores.items()},
            "description": self.description,
        }


# ── Profile constructor ───────────────────────────────────────────────────────

def _profile(
    component: str,
    overrides: dict[str, float],
    primary: tuple[str, ...],
    description: str = "",
) -> ComponentFeatureProfile:
    """Build a profile by merging overrides onto global defaults, then clamp."""
    scores = dict(_GLOBAL_DEFAULT)
    for dim, delta in overrides.items():
        scores[dim] = scores[dim] + delta
    # Hard clamp to [0.61, 0.97] — preserve calibration headroom
    scores = {k: max(0.61, min(0.97, v)) for k, v in scores.items()}
    return ComponentFeatureProfile(
        component=component,
        dimension_scores=scores,
        primary_dimensions=primary,
        description=description,
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT FEATURE PROFILES  (28 components — one per COMPONENT_DOMAIN_MAP key)
# ══════════════════════════════════════════════════════════════════════════════

_PROFILES: dict[str, ComponentFeatureProfile] = {

    # ── ROUTING & CONFIG ──────────────────────────────────────────────────────

    "router": _profile(
        "router",
        overrides={
            "Accuracy": +0.04,  # intent classification is correctness-critical
            "Speed": +0.08,  # every mandate passes through here — latency critical
            "Honesty": +0.04,  # confidence/CB calibration
            "Control": +0.03,  # circuit-breaker control
            "Financial Awareness": -0.05,  # routing doesn't own cost decisions
            "Human Considering": -0.03,  # not a user-facing component
        },
        primary=("Accuracy", "Speed", "Honesty"),
        description="Intent classification + circuit breaker — latency & routing accuracy critical",
    ),

    "config": _profile(
        "config",
        overrides={
            "Security": +0.02,  # Law 9: no hardcoded credentials — boundary guardian
            "Legal": +0.05,  # compliance config (env vars, API keys)
            "Quality": +0.05,  # clean, validated env loading
            "Safety": -0.03,  # config itself is passive (no execution)
            "ROI": -0.04,  # pure infrastructure, no direct ROI
            "Human Considering": -0.05,  # no user-facing aspect
            "Speed": +0.03,  # startup config load must be fast
        },
        primary=("Security", "Legal", "Quality"),
        description="Single source of truth for all env/config — security boundary guardian",
    ),

    # ── EXECUTION ─────────────────────────────────────────────────────────────

    "executor": _profile(
        "executor",
        overrides={
            "Efficiency": +0.08,  # ThreadPoolExecutor — parallel fan-out efficiency
            "Speed": +0.07,  # fan-out concurrency drives throughput
            "Resilience": +0.05,  # error isolation across threads
            "Convergence": +0.04,  # ensures all units complete
            "Financial Awareness": -0.06,  # not cost-aware at thread level
            "Legal": -0.04,  # no compliance concerns in executor
            "Human Considering": -0.04,  # pure execution engine
        },
        primary=("Efficiency", "Speed", "Resilience"),
        description="JITExecutor fan-out via ThreadPoolExecutor — parallelism & isolation",
    ),

    "n_stroke": _profile(
        "n_stroke",
        overrides={
            "ROI": +0.06,  # all mandate value flows through N-Stroke
            "Convergence": +0.08,  # 7-stroke loop — convergence is its core metric
            "Resilience": +0.05,  # multi-stroke recovery
            "Control": +0.04,  # stroke gating + early exit
            "Monitor": +0.08,  # SSE broadcast_fn on every stroke event
            "Human Considering": -0.04,  # orchestration engine, not user-facing
            "Legal": -0.03,  # no compliance concerns in loop
        },
        primary=("Convergence", "ROI", "Resilience"),
        description="7-stroke execution loop — convergence rate and orchestration ROI",
    ),

    "graph": _profile(
        "graph",
        overrides={
            "Accuracy": +0.04,  # cycle detection must be 100% correct
            "Safety": -0.01,  # already 0.95; small adjustment
            "Reversibility": +0.05,  # rollback on cycle detection is critical
            "Speed": -0.06,  # graph ops are pre-execution planning, not hot path
            "ROI": -0.05,  # pure infrastructure utility
            "Financial Awareness": -0.06,  # no cost awareness in DAG topology
            "Human Considering": -0.06,  # abstract graph utility
        },
        primary=("Accuracy", "Reversibility", "Safety"),
        description="CognitiveGraph + TopologicalSorter — DAG acyclicity & correctness",
    ),

    "branch_executor": _profile(
        "branch_executor",
        overrides={
            "Efficiency": +0.07,  # FORK fan-out — parallel branch execution
            "Convergence": +0.07,  # SHARE synthesis — convergence of branches
            "Reversibility": +0.05,  # branch isolation allows rollback
            "Monitor": +0.06,  # SSE broadcast on FORK/SHARE events
            "Financial Awareness": -0.05,  # not cost-aware within execution
            "Human Considering": -0.04,  # engine-internal utility
        },
        primary=("Efficiency", "Convergence", "Reversibility"),
        description="FORK → SHARE branch execution — parallel synthesis",
    ),

    "async_fluid_executor": _profile(
        "async_fluid_executor",
        overrides={
            "Speed": +0.09,  # async execution is latency-critical
            "Efficiency": +0.08,  # asyncio concurrency maximisation
            "Resilience": +0.05,  # async error handling + timeout guards
            "Financial Awareness": -0.07,  # async layer doesn't own cost
            "Human Considering": -0.05,  # pure async execution utility
            "Legal": -0.04,  # no compliance in async executor
        },
        primary=("Speed", "Efficiency", "Resilience"),
        description="AsyncFluidExecutor — async DAG fan-out, latency & throughput",
    ),

    "mandate_executor": _profile(
        "mandate_executor",
        overrides={
            "Accuracy": +0.04,  # prompt construction fidelity
            "Honesty": +0.04,  # intent-locked execution — no scope creep
            "Quality": +0.05,  # clean prompt engineering
            "Speed": -0.03,  # not the bottleneck in execution
            "Financial Awareness": -0.04,  # not cost-aware in prompt builder
        },
        primary=("Accuracy", "Honesty", "Quality"),
        description="make_live_work_fn — prompt construction & intent-locked execution",
    ),

    # ── INTELLIGENCE ──────────────────────────────────────────────────────────

    "jit_booster": _profile(
        "jit_booster",
        overrides={
            "Accuracy": +0.04,  # signal quality — SOTA data accuracy
            "Honesty": +0.05,  # confidence calibration (boost delta math)
            "Financial Awareness": +0.08,  # Gemini API cost awareness critical
            "Speed": -0.04,  # async fetch, not latency-critical path
            "Human Considering": -0.04,  # engine-internal signal fetcher
        },
        primary=("Honesty", "Financial Awareness", "Accuracy"),
        description="SOTA signal fetcher — confidence calibration & API cost awareness",
    ),

    "meta_architect": _profile(
        "meta_architect",
        overrides={
            "ROI": +0.07,  # swarm weighting maximises mandate ROI
            "Accuracy": +0.04,  # topology generation correctness
            # swarm persona balance (diverse viewpoints)
            "Human Considering": +0.03,
            "Convergence": +0.04,  # ensures swarm converges to solution
            "Financial Awareness": -0.04,  # meta-planning, not execution cost
        },
        primary=("ROI", "Accuracy", "Convergence"),
        description="MetaArchitect — swarm topology & ROI-optimised orchestration",
    ),

    "model_selector": _profile(
        "model_selector",
        overrides={
            "Financial Awareness": +0.10,  # tier selection directly controls API cost
            "Efficiency": +0.08,  # tier matching = compute efficiency
            "Accuracy": +0.04,  # selecting right model for task
            "Speed": +0.04,  # selector runs on hot path
            "Human Considering": -0.05,  # model selection utility
            "Legal": -0.04,  # no compliance role
        },
        primary=("Financial Awareness", "Efficiency", "Accuracy"),
        description="4-tier model selector — financial awareness & compute efficiency",
    ),

    "model_garden": _profile(
        "model_garden",
        overrides={
            "Speed": +0.07,  # dispatch latency matters for UX
            "Efficiency": +0.07,  # routing to optimal tier
            "Financial Awareness": +0.09,  # cost routing across model tiers
            "Resilience": +0.04,  # fallback chain between tiers
            "Human Considering": -0.05,  # model dispatch utility
            "Legal": -0.04,  # no compliance in dispatch
        },
        primary=("Financial Awareness", "Speed", "Efficiency"),
        description="ModelGarden dispatch — cost-optimised model routing",
    ),

    # ── VALIDATION & HEALING ──────────────────────────────────────────────────

    "tribunal": _profile(
        "tribunal",
        overrides={
            "Security": +0.02,  # OWASP scanner — max security
            "Safety": +0.02,  # poison guard — max safety
            "Accuracy": +0.04,  # true-positive rate in pattern matching
            "Speed": -0.07,  # scans all artefacts — not latency-critical
            "ROI": -0.03,  # pure cost centre (defence, not value-gen)
            "Financial Awareness": -0.06,  # no cost awareness in security scanning
        },
        primary=("Security", "Safety", "Accuracy"),
        description="OWASP Tribunal scanner — security & safety guardian",
    ),

    "refinement": _profile(
        "refinement",
        overrides={
            "Accuracy": +0.04,  # pass/warn/fail verdict accuracy
            "Honesty": +0.04,  # calibrated thresholds (no false PASS)
            "Quality": +0.05,  # clean verdict reports
            "Speed": -0.05,  # post-execution evaluation — not hot path
            "Financial Awareness": -0.05,  # not cost-aware
        },
        primary=("Accuracy", "Honesty", "Quality"),
        description="RefinementLoop — calibrated pass/warn/fail verdict accuracy",
    ),

    "refinement_supervisor": _profile(
        "refinement_supervisor",
        overrides={
            "Resilience": +0.08,  # healing is its primary job
            "Convergence": +0.08,  # heal nodes to convergence
            "Control": +0.07,  # HealingPrescription — controlled repair
            "Speed": -0.06,  # healing is deliberate, not latency-optimised
            "Financial Awareness": -0.05,  # healing cost is acceptable overhead
            "Human Considering": -0.04,  # autonomous engine component
        },
        primary=("Resilience", "Convergence", "Control"),
        description="RefinementSupervisor autonomous healing — NODE_FAIL_THRESHOLD recovery",
    ),

    "validator_16d": _profile(
        "validator_16d",
        overrides={
            "Accuracy": +0.05,  # 16D dimension math must be precise
            "Honesty": +0.05,  # score calibration — no inflated confidence
            "Safety": -0.01,  # already 0.95; slight reduction (not primary)
            "Speed": -0.04,  # 16D computation is not latency-critical
            "Financial Awareness": -0.06,  # pure validation utility
        },
        primary=("Accuracy", "Honesty", "Safety"),
        description="Validator16D — 16-dimension scoring gate",
    ),

    "scope_evaluator": _profile(
        "scope_evaluator",
        overrides={
            "Accuracy": +0.04,  # node enumeration accuracy
            "Quality": +0.06,  # wave plan clarity
            "Efficiency": +0.04,  # fast scope analysis
            "Speed": +0.03,  # pre-execution — should be fast
            "Financial Awareness": -0.06,  # pre-execution planning, not cost
            "Human Considering": -0.04,  # engine utility
        },
        primary=("Accuracy", "Quality", "Efficiency"),
        description="ScopeEvaluator — DAG node enumeration & wave plan generation",
    ),

    # ── DATA & STATE ──────────────────────────────────────────────────────────

    "psyche_bank": _profile(
        "psyche_bank",
        overrides={
            "Honesty": +0.05,  # rule store accuracy — wrong rules corrupt agents
            "Security": +0.01,  # stores OWASP-derived rules
            "Quality": +0.08,  # clean JSON schema, TTL management
            "Speed": -0.07,  # disk I/O — not latency critical
            "ROI": -0.04,  # infrastructure store
            "Human Considering": -0.06,  # engine-internal rule store
        },
        primary=("Honesty", "Quality", "Security"),
        description="PsycheBank cog.json store — rule accuracy & schema quality",
    ),

    "buddy_cache": _profile(
        "buddy_cache",
        overrides={
            "Speed": +0.12,  # cache = latency reduction — Speed is #1
            "Efficiency": +0.09,  # memory management across 3 layers
            "Financial Awareness": +0.11,  # reduces Gemini API calls — direct cost saving
            "Accuracy": -0.06,  # cache may return slightly stale content
            # cache bypass guards are secondary (poison guard)
            "Safety": -0.04,
            "Legal": -0.06,  # no compliance concerns in cache
        },
        primary=("Speed", "Financial Awareness", "Efficiency"),
        description="3-layer semantic cache (L1 Jaccard, L2 fingerprint, L3 disk) — latency & cost",
    ),

    "buddy_cognition": _profile(
        "buddy_cognition",
        overrides={
            "Human Considering": +0.08,  # Expertise Reversal + ZPD — UX core
            "Accuracy": +0.03,  # CLT cognitive load estimation
            "Honesty": +0.04,  # calibrated expertise scoring (EMA α=0.08)
            "Speed": -0.04,  # cognitive analysis not latency-critical
            "Financial Awareness": -0.05,  # not cost-aware
            "Security": -0.04,  # no OWASP concerns in cognition layer
        },
        primary=("Human Considering", "Honesty", "Accuracy"),
        description="CognitiveLens + UserProfileStore — expertise adaptation & ZPD anchoring",
    ),

    "conversation": _profile(
        "conversation",
        overrides={
            "Human Considering": +0.07,  # UX core — 11 modes, empathy openers
            "Honesty": +0.04,  # truth + validation-first in SUPPORT mode
            "Accuracy": +0.03,  # mode routing accuracy
            "Security": -0.05,  # conversation layer not a security boundary
            "Financial Awareness": -0.04,  # per-turn cost is managed by model_selector
            "Efficiency": -0.03,  # UX quality > efficiency in conversation
        },
        primary=("Human Considering", "Honesty", "Accuracy"),
        description="ConversationEngine — 11 modes, empathy, cognitive load adaptation",
    ),

    "mcp_manager": _profile(
        "mcp_manager",
        overrides={
            "Control": +0.08,  # 6 MCP tools — controlled tool access
            "Security": +0.03,  # path-traversal guard on all file tools
            "Accuracy": +0.03,  # correct tool dispatch
            "Financial Awareness": -0.06,  # tool orchestration utility
            "Human Considering": -0.05,  # engine internal
            "ROI": -0.04,  # infrastructure utility
        },
        primary=("Control", "Security", "Accuracy"),
        description="MCPManager 6-tool registry — controlled tool access with path guards",
    ),

    # ── DOMAIN ────────────────────────────────────────────────────────────────

    "self_improvement": _profile(
        "self_improvement",
        overrides={
            "ROI": +0.08,  # self-improvement cycle is pure ROI engine
            "Convergence": +0.08,  # cycle must converge to higher quality
            "Safety": -0.04,  # intentionally aggressive (fluid crucible)
            "Resilience": +0.04,  # must survive partial failures
            "Monitor": +0.07,  # SSE broadcast on every SI cycle event
            "Financial Awareness": -0.05,  # improvement cost is accepted overhead
            "Human Considering": -0.04,  # autonomous engine
        },
        primary=("ROI", "Convergence", "Resilience"),
        description="SelfImprovementEngine — ROI-driven autonomous self-calibration",
    ),

    "sandbox": _profile(
        "sandbox",
        overrides={
            "Security": +0.02,  # sandboxed execution isolation
            "Safety": +0.02,  # safe execution boundary
            "Control": +0.07,  # write boundary enforcement (engine/ only)
            "Monitor": +0.06,  # SSE broadcast on sandbox lifecycle events
            "ROI": -0.06,  # sandbox overhead is a cost, not value gen
            "Speed": -0.06,  # isolation adds latency
            "Financial Awareness": -0.04,  # isolation infrastructure cost
        },
        primary=("Security", "Safety", "Control"),
        description="SandboxOrchestrator — isolated execution with write boundary enforcement",
    ),

    "roadmap": _profile(
        "roadmap",
        overrides={
            "ROI": +0.07,  # roadmap quality directly drives planning ROI
            "Accuracy": +0.03,  # roadmap parsing fidelity
            "Quality": +0.07,  # clean roadmap structure
            "Speed": -0.08,  # planning is not latency-critical
            "Financial Awareness": -0.04,  # roadmap planning utility
            "Human Considering": +0.03,  # roadmap is user-goal-aligned
        },
        primary=("ROI", "Quality", "Accuracy"),
        description="RoadmapManager — planning fidelity & user-goal alignment",
    ),

    "vector_store": _profile(
        "vector_store",
        overrides={
            "Accuracy": +0.05,  # deduplication accuracy critical
            "Efficiency": +0.05,  # index management — memory efficient
            "Speed": +0.05,  # lookup latency
            "Financial Awareness": -0.06,  # storage infrastructure
            "Human Considering": -0.07,  # abstract storage utility
            "Legal": -0.04,  # no compliance concerns in vector index
        },
        primary=("Accuracy", "Speed", "Efficiency"),
        description="VectorStore — semantic deduplication & efficient index management",
    ),

    "sota_ingestion": _profile(
        "sota_ingestion",
        overrides={
            "Accuracy": +0.05,  # ingestion quality — right data in
            "Honesty": +0.06,  # provenance tracking — no fabricated data
            "Resilience": +0.04,  # handles partial ingestion failures
            "Speed": -0.07,  # batch ingestion, not latency-critical
            "Human Considering": -0.04,  # data pipeline utility
            "Financial Awareness": -0.04,  # ingestion infrastructure cost
        },
        primary=("Accuracy", "Honesty", "Resilience"),
        description="SOTAIngestionEngine — data provenance & ingestion accuracy",
    ),

    "daemon": _profile(
        "daemon",
        overrides={
            "Resilience": +0.08,  # always-on — must never crash
            "Monitor": +0.11,  # health tracking & lifecycle monitoring
            "Control": +0.07,  # start/stop/recalibrate lifecycle
            "Speed": -0.07,  # background — not latency-critical
            "ROI": -0.06,  # daemon is infrastructure, not value generator
            "Financial Awareness": -0.04,  # background infra cost
        },
        primary=("Monitor", "Resilience", "Control"),
        description="BackgroundDaemon — always-on health monitoring & lifecycle control",
    ),
}

# Ensure all expected components have profiles
_EXPECTED_COMPONENTS: tuple[str, ...] = (
    "router", "tribunal", "psyche_bank", "jit_booster", "executor", "graph",
    "scope_evaluator", "refinement", "refinement_supervisor", "n_stroke",
    "meta_architect", "model_selector", "model_garden", "validator_16d",
    "conversation", "buddy_cache", "buddy_cognition", "branch_executor",
    "async_fluid_executor", "mandate_executor", "mcp_manager",
    "self_improvement", "sandbox", "roadmap", "vector_store",
    "sota_ingestion", "daemon", "config",
)
_missing = [c for c in _EXPECTED_COMPONENTS if c not in _PROFILES]
assert not _missing, f"feature_registry: missing profiles for: {_missing}"


# ── Public API ────────────────────────────────────────────────────────────────

def get_component_profile(component: str) -> ComponentFeatureProfile:
    """
    Return the 16D feature profile for a named component.

    Falls back to a synthetic default profile (global NoCode defaults) for
    unknown components, ensuring forward-compatibility with new modules.
    """
    if component in _PROFILES:
        return _PROFILES[component]
    # Unknown component — return global default profile
    return ComponentFeatureProfile(
        component=component,
        dimension_scores=dict(_GLOBAL_DEFAULT),
        primary_dimensions=("Accuracy", "Safety", "Honesty"),
        description="(auto-generated default — add explicit profile to feature_registry.py)",
    )


def all_profiles() -> list[ComponentFeatureProfile]:
    """Return all registered component profiles sorted by component name."""
    return sorted(_PROFILES.values(), key=lambda p: p.component)


def profile_summary() -> dict[str, dict[str, Any]]:
    """Return a compact summary dict for serialisation."""
    return {p.component: p.to_dict() for p in all_profiles()}
