# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.deep_introspector.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/deep_introspector.py — TooLoo's Ultimate Self-Awareness Engine.

Deep introspection layer that sits atop the CognitiveMap and provides:
  * Per-module health scoring (complexity, size, dependency depth)
  * Function-level cross-reference tracking (who calls whom)
  * Dead code detection (public functions never referenced elsewhere)
  * System health dashboard ("break-glass" overview)
  * Churn/entropy analysis (which modules are most complex/unstable)
  * Semantic knowledge graph (module roles, criticality, failsafes)
  * Predictive cascade analysis (failure likelihood from blast radius)

Integration:
  The DeepIntrospector enriches the CognitiveMap via `enrich_map()` and
  provides its own `/v2/introspector/*` REST endpoints.

Thread Safety:
  All mutations hold ``_lock`` (RLock).  Read paths are lock-free.
  Singleton via ``get_instance()`` with double-checked locking.

Law 17 Compliance:
  Stateless analysis methods — all results are immutable snapshots.
  Internal state is rebuilt on demand; no mutable data escapes to callers.
"""
from __future__ import annotations

import ast
import logging
from engine.auto_fixer import AutoFixLoop
import math
import re
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Repository root ───────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parents[1]
_ENGINE_ROOT = _REPO_ROOT / "engine"

# ── Regex patterns ────────────────────────────────────────────────────────────
_RE_FROM_IMPORT = re.compile(
    r"^from\s+engine\.(\w+)\s+import\s+(.+)", re.MULTILINE
)
_RE_FUNCTION_CALL = re.compile(r"\b(\w+)\s*\(")
_RE_CLASS_DEF = re.compile(r"^class\s+(\w+)", re.MULTILINE)
_RE_FUNC_DEF = re.compile(r"^(?:async\s+)?def\s+(\w+)", re.MULTILINE)

# ── Semantic knowledge: module roles & criticality ────────────────────────────
_MODULE_KNOWLEDGE: dict[str, dict[str, Any]] = {
    "n_stroke": {
        "role": "Primary autonomous execution loop (up to 7 strokes)",
        "critical": True,
        "failsafe": "RefinementSupervisor",
        "layer": "execution",
    },
    "mandate_executor": {
        "role": "LLM-powered DAG node executor (closure factory)",
        "critical": True,
        "failsafe": "Tribunal + circuit breaker",
        "layer": "execution",
    },
    "executor": {
        "role": "JIT fan-out via ThreadPoolExecutor (Law 17)",
        "critical": True,
        "failsafe": "timeout + max_workers cap",
        "layer": "execution",
    },
    "async_fluid_executor": {
        "role": "Async event-driven execution fabric (25-40% latency gain)",
        "critical": True,
        "failsafe": "asyncio.wait_for timeout",
        "layer": "execution",
    },
    "tribunal": {
        "role": "OWASP poison scanner — security gate on every artefact",
        "critical": True,
        "failsafe": "tombstone + PsycheBank capture",
        "layer": "validation",
    },
    "validator_16d": {
        "role": "16-dimension quality validator (ROI through reversibility)",
        "critical": True,
        "failsafe": "minimum threshold rejection",
        "layer": "validation",
    },
    "refinement": {
        "role": "Post-execution evaluate-and-refine loop",
        "critical": False,
        "failsafe": "pass-through on error",
        "layer": "validation",
    },
    "refinement_supervisor": {
        "role": "Autonomous healing (MCP + SOTA → HealingPrescription)",
        "critical": True,
        "failsafe": "NODE_FAIL_THRESHOLD + circuit breaker",
        "layer": "healing",
    },
    "router": {
        "role": "Intent classification + confidence circuit breaker",
        "critical": True,
        "failsafe": "UNKNOWN fallback + CB threshold",
        "layer": "routing",
    },
    "jit_booster": {
        "role": "SOTA signal fetcher (Gemini live + structured fallback)",
        "critical": True,
        "failsafe": "structured catalogue fallback",
        "layer": "intelligence",
    },
    "meta_architect": {
        "role": "Dynamic DAG synthesis + confidence proof scoring",
        "critical": False,
        "failsafe": "single-node fallback DAG",
        "layer": "intelligence",
    },
    "model_selector": {
        "role": "Dynamic tier selection (T1-T4 escalation per stroke)",
        "critical": False,
        "failsafe": "default to T2",
        "layer": "intelligence",
    },
    "model_garden": {
        "role": "Multi-provider model registry (Google + Anthropic + Vertex)",
        "critical": False,
        "failsafe": "single-provider fallback",
        "layer": "intelligence",
    },
    "graph": {
        "role": "Pure DAG logic (cycle detection, provenance, topo-sort)",
        "critical": True,
        "failsafe": "CycleDetectedError + rollback",
        "layer": "core",
    },
    "config": {
        "role": "Single source of truth — env vars + typed settings",
        "critical": True,
        "failsafe": "default values for all settings",
        "layer": "core",
    },
    "conversation": {
        "role": "Multi-turn Buddy engine (intent-aware DAG planning)",
        "critical": False,
        "failsafe": "graceful degradation to single-turn",
        "layer": "conversation",
    },
    "buddy_cognition": {
        "role": "Cognitive lens (Sweller, Kahneman, Miller theories)",
        "critical": False,
        "failsafe": "default novice profile",
        "layer": "conversation",
    },
    "buddy_memory": {
        "role": "Persistent cross-session memory (Tribunal invariant)",
        "critical": False,
        "failsafe": "empty memory fallback",
        "layer": "conversation",
    },
    "buddy_cache": {
        "role": "3-layer semantic cache (L1 Jaccard, L2 fingerprint, L3 disk)",
        "critical": False,
        "failsafe": "cache miss → fresh generation",
        "layer": "conversation",
    },
    "cognitive_map": {
        "role": "Live cognitive self-map (networkx DAG of codebase)",
        "critical": True,
        "failsafe": "rebuild() on first access",
        "layer": "self-awareness",
    },
    "bus": {
        "role": "Unified notification bus (pub/sub INFO→CRITICAL)",
        "critical": False,
        "failsafe": "silent drop on subscriber error",
        "layer": "infrastructure",
    },
    "stance": {
        "role": "Cognitive stance engine (IDEATION/DEEP_EXECUTION/etc.)",
        "critical": False,
        "failsafe": "MAINTENANCE default stance",
        "layer": "intelligence",
    },
    "scope_evaluator": {
        "role": "Pre-execution wave-plan analysis (nodes, waves, parallelism)",
        "critical": False,
        "failsafe": "single-wave linear plan",
        "layer": "planning",
    },
    "psyche_bank": {
        "role": "Thread-safe .cog.json rule store (dedup, TTL, max 10k)",
        "critical": False,
        "failsafe": "empty bank on load error",
        "layer": "memory",
    },
    "self_improvement": {
        "role": "Self-improvement autopilot (Ouroboros cycle)",
        "critical": True,
        "failsafe": "regression gate blocks bad patches",
        "layer": "self-awareness",
    },
    "sandbox": {
        "role": "Isolated execution sandbox (spawn_repo capability)",
        "critical": False,
        "failsafe": "timeout + temp dir cleanup",
        "layer": "execution",
    },
    "parallel_validation": {
        "role": "Parallel Tribunal + 16D + tests pipeline (Law 8)",
        "critical": False,
        "failsafe": "sequential fallback on thread error",
        "layer": "validation",
    },
    "healing_guards": {
        "role": "Convergence + reversibility guards for healing",
        "critical": False,
        "failsafe": "reject heal if guard fails",
        "layer": "healing",
    },
    "deep_introspector": {
        "role": "Deep self-awareness engine (health, cross-refs, dead code)",
        "critical": False,
        "failsafe": "graceful empty results on analysis error",
        "layer": "self-awareness",
    },
    "daemon": {
        "role": "Background ROI scoring + autonomous proposal daemon",
        "critical": False,
        "failsafe": "daemon stop on unhandled error",
        "layer": "infrastructure",
    },
    "mcp_manager": {
        "role": "MCP tool dispatch (6 built-in tools)",
        "critical": False,
        "failsafe": "tool not-found error passthrough",
        "layer": "execution",
    },
}

# ── Layers for grouping ──────────────────────────────────────────────────────
_LAYER_ORDER = [
    "core", "routing", "planning", "intelligence", "execution",
    "validation", "healing", "self-awareness", "conversation",
    "memory", "infrastructure",
]


# ── Data classes ──────────────────────────────────────────────────────────────

class FunctionRef:
    """A cross-reference between two functions across modules."""
    __slots__ = ("source_module", "source_fn", "target_module",
                 "target_fn", "line_no")

    def __init__(self, source_module: str, source_fn: str,
                 target_module: str, target_fn: str, line_no: int) -> None:
        self.source_module = source_module
        self.source_fn = source_fn
        self.target_module = target_module
        self.target_fn = target_fn
        self.line_no = line_no

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": f"{self.source_module}.{self.source_fn}",
            "target": f"{self.target_module}.{self.target_fn}",
            "line": self.line_no,
        }


class ModuleHealth:
    """Health assessment for a single engine module."""
    __slots__ = (
        "module_name", "file_path", "line_count", "class_count",
        "function_count", "public_fn_count", "import_count",
        "complexity_score", "dependency_depth", "dependents_count",
        "dead_fn_count", "dead_fns", "health_score", "layer",
        "critical", "role",
    )

    def __init__(self, module_name: str, **kwargs: Any) -> None:
        self.module_name = module_name
        self.file_path = kwargs.get("file_path", "")
        self.line_count = kwargs.get("line_count", 0)
        self.class_count = kwargs.get("class_count", 0)
        self.function_count = kwargs.get("function_count", 0)
        self.public_fn_count = kwargs.get("public_fn_count", 0)
        self.import_count = kwargs.get("import_count", 0)
        self.complexity_score = kwargs.get("complexity_score", 0.0)
        self.dependency_depth = kwargs.get("dependency_depth", 0)
        self.dependents_count = kwargs.get("dependents_count", 0)
        self.dead_fn_count = kwargs.get("dead_fn_count", 0)
        self.dead_fns = kwargs.get("dead_fns", [])
        self.health_score = kwargs.get("health_score", 1.0)
        self.layer = kwargs.get("layer", "unknown")
        self.critical = kwargs.get("critical", False)
        self.role = kwargs.get("role", "")

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module_name,
            "file_path": self.file_path,
            "line_count": self.line_count,
            "class_count": self.class_count,
            "function_count": self.function_count,
            "public_fn_count": self.public_fn_count,
            "import_count": self.import_count,
            "complexity": round(self.complexity_score, 3),
            "dependency_depth": self.dependency_depth,
            "dependents_count": self.dependents_count,
            "dead_fn_count": self.dead_fn_count,
            "dead_fns": self.dead_fns[:10],
            "health_score": round(self.health_score, 3),
            "layer": self.layer,
            "critical": self.critical,
            "role": self.role,
        }


class SystemHealthReport:
    """Aggregated system health snapshot — the 'break-glass' dashboard."""

    def __init__(
        self,
        *,
        module_count: int = 0,
        avg_health: float = 0.0,
        min_health_module: str = "",
        min_health_score: float = 0.0,
        critical_modules_healthy: int = 0,
        critical_modules_total: int = 0,
        total_dead_fns: int = 0,
        total_cross_refs: int = 0,
        total_lines: int = 0,
        layer_summary: dict[str, Any] | None = None,
        status: str = "green",
        recommendations: list[str] | None = None,
        built_at: float = 0.0,
        build_ms: float = 0.0,
    ) -> None:
        self.module_count = module_count
        self.avg_health = avg_health
        self.min_health_module = min_health_module
        self.min_health_score = min_health_score
        self.critical_modules_healthy = critical_modules_healthy
        self.critical_modules_total = critical_modules_total
        self.total_dead_fns = total_dead_fns
        self.total_cross_refs = total_cross_refs
        self.total_lines = total_lines
        self.layer_summary = layer_summary or {}
        self.status = status
        self.recommendations = recommendations or []
        self.built_at = built_at
        self.build_ms = build_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "module_count": self.module_count,
            "avg_health": round(self.avg_health, 3),
            "min_health": {
                "module": self.min_health_module,
                "score": round(self.min_health_score, 3),
            },
            "critical_modules": {
                "healthy": self.critical_modules_healthy,
                "total": self.critical_modules_total,
            },
            "total_dead_functions": self.total_dead_fns,
            "total_cross_references": self.total_cross_refs,
            "total_lines_of_code": self.total_lines,
            "layers": self.layer_summary,
            "recommendations": self.recommendations[:10],
            "built_at": self.built_at,
            "build_ms": round(self.build_ms, 1),
        }


# ── Main class ────────────────────────────────────────────────────────────────

class DeepIntrospector:
    """
    TooLoo's ultimate self-awareness engine.

    Performs deep static analysis of the engine codebase, tracks function-level
    cross-references, scores module health, detects dead code, and provides
    a unified system health dashboard.

    Usage::

        di = DeepIntrospector.get_instance()
        report = di.system_health()          # break-glass overview
        health = di.module_health("router")  # per-module deep dive
        refs = di.cross_refs("router")       # who calls router functions
        dead = di.dead_functions()            # unreferenced public functions
        kg = di.knowledge_graph()            # semantic module metadata
        cascade = di.cascade_analysis("engine/router.py")  # failure prediction

    Singleton semantics: ``get_instance()`` returns the same object for the
    lifetime of the process.  Call ``rebuild()`` to force a full re-analysis.
    """

    _instance: "DeepIntrospector | None" = None
    _instance_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._built = False
        self._build_ts: float = 0.0

        # Per-module health data
        self._health: dict[str, ModuleHealth] = {}

        # Cross-reference index: target_module → [FunctionRef]
        self._xrefs: dict[str, list[FunctionRef]] = defaultdict(list)

        # Inverted xref: (target_module, target_fn) → set of source_modules
        self._fn_callers: dict[tuple[str, str], set[str]] = defaultdict(set)

        # All public functions per module
        self._public_fns: dict[str, list[str]] = {}

        # All exported symbols per module (from imports)
        self._exported_symbols: dict[str, set[str]] = defaultdict(set)

        # Cached system health report
        self._system_report: SystemHealthReport | None = None

        # Update callbacks (for SSE broadcast)
        self._on_update: list[Any] = []

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "DeepIntrospector":
        """Return the process-level singleton, building on first call."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    inst = cls()
                    inst.rebuild()
                    cls._instance = inst
        return cls._instance

    # ── Public API ─────────────────────────────────────────────────────────────

    def rebuild(self) -> None:
        """Full deep analysis of all engine modules."""
        t0 = time.monotonic()
        with self._lock:
            self._health.clear()
            self._xrefs.clear()
            self._fn_callers.clear()
            self._public_fns.clear()
            self._exported_symbols.clear()
            self._system_report = None

            # Phase 1: Collect all module metadata
            source_files = sorted(_ENGINE_ROOT.glob("*.py"))
            for path in source_files:
                if path.name == "__init__.py":
                    continue
                self._analyze_module(path)

            # Phase 2: Build cross-references
            for path in source_files:
                if path.name == "__init__.py":
                    continue
                self._build_cross_refs(path)

            # Phase 3: Detect dead code
            self._detect_dead_code()

            # Phase 4: Compute health scores
            self._compute_health_scores()

            self._built = True
            self._build_ts = time.monotonic() - t0

        self._fire_update({
            "event": "deep_introspection_complete",
            "module_count": len(self._health),
            "build_ms": round(self._build_ts * 1000, 1),
        })
        logger.info(
            "DeepIntrospector rebuilt: %d modules in %.1f ms",
            len(self._health), self._build_ts * 1000,
        )

    def system_health(self) -> SystemHealthReport:
        """Return the aggregated system health snapshot."""
        if not self._built:
            self.rebuild()
        if self._system_report is None:
            self._system_report = self._build_system_report()
        return self._system_report

    def module_health(self, module_name: str) -> ModuleHealth | None:
        """Return health data for a specific module."""
        if not self._built:
            self.rebuild()
        return self._health.get(module_name)

    def all_module_health(self) -> list[ModuleHealth]:
        """Return health data for all modules, sorted by health score."""
        if not self._built:
            self.rebuild()
        return sorted(
            self._health.values(), key=lambda h: h.health_score
        )

    def cross_refs(self, module_name: str) -> list[FunctionRef]:
        """Return all cross-references targeting functions in ``module_name``."""
        if not self._built:
            self.rebuild()
        return list(self._xrefs.get(module_name, []))

    def all_cross_refs(self) -> dict[str, list[dict[str, Any]]]:
        """Return all cross-references grouped by target module."""
        if not self._built:
            self.rebuild()
        return {
            mod: [r.to_dict() for r in refs]
            for mod, refs in self._xrefs.items()
        }

    def dead_functions(self) -> list[dict[str, Any]]:
        """Return public functions that are never referenced by other modules."""
        if not self._built:
            self.rebuild()
        dead: list[dict[str, Any]] = []
        for module_name, fns in self._public_fns.items():
            for fn_name in fns:
                key = (module_name, fn_name)
                if not self._fn_callers.get(key):
                    health = self._health.get(module_name)
                    dead.append({
                        "module": module_name,
                        "function": fn_name,
                        "file_path": health.file_path if health else "",
                    })
        return dead

    def knowledge_graph(self) -> dict[str, Any]:
        """Return semantic knowledge graph — module roles and relationships."""
        if not self._built:
            self.rebuild()
        modules: list[dict[str, Any]] = []
        for mod_name, health in self._health.items():
            short = mod_name.replace("engine.", "")
            knowledge = _MODULE_KNOWLEDGE.get(short, {})
            modules.append({
                "module": mod_name,
                "role": knowledge.get("role", health.role or "Unknown"),
                "layer": knowledge.get("layer", health.layer),
                "critical": knowledge.get("critical", health.critical),
                "failsafe": knowledge.get("failsafe", "none"),
                "health_score": round(health.health_score, 3),
                "dependents": health.dependents_count,
                "dependencies": health.import_count,
            })
        # Group by layer
        layers: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for m in modules:
            layers[m["layer"]].append(m)
        return {
            "total_modules": len(modules),
            "layers": {
                layer: layers.get(layer, [])
                for layer in _LAYER_ORDER
                if layer in layers
            },
            "modules": modules,
        }

    def cascade_analysis(self, file_path: str) -> dict[str, Any]:
        """Predict failure cascade impact if ``file_path`` is modified.

        Uses dependency depth + dependents count + criticality to produce
        a failure likelihood score for each affected module.
        """
        if not self._built:
            self.rebuild()

        # Get blast radius from CognitiveMap (lazy import to avoid circular)
        from engine.cognitive_map import get_cognitive_map
        cmap = get_cognitive_map()
        affected_files = cmap.blast_radius(file_path)

        stem = Path(file_path).stem
        source_health = self._health.get(stem)
        source_score = source_health.health_score if source_health else 0.5

        cascade: list[dict[str, Any]] = []
        for af in affected_files:
            af_stem = Path(af).stem
            target_health = self._health.get(af_stem)
            if not target_health:
                continue
            # Cascade score: lower health + more deps + critical = higher risk
            risk = (1.0 - target_health.health_score) * 0.4
            risk += min(target_health.dependency_depth / 10.0, 0.3)
            risk += 0.2 if target_health.critical else 0.0
            risk += (1.0 - source_score) * 0.1
            risk = min(risk, 1.0)
            cascade.append({
                "module": af_stem,
                "file_path": af,
                "failure_risk": round(risk, 3),
                "health_score": round(target_health.health_score, 3),
                "critical": target_health.critical,
                "role": target_health.role,
            })

        cascade.sort(key=lambda c: c["failure_risk"], reverse=True)
        return {
            "source": file_path,
            "source_health": round(source_score, 3),
            "affected_count": len(cascade),
            "cascade": cascade,
            "max_risk": cascade[0]["failure_risk"] if cascade else 0.0,
        }

    def enrich_map(self) -> dict[str, Any]:
        """Return enrichment data for the CognitiveMap.

        This provides health scores, dead code counts, and cross-ref counts
        per module that CognitiveMap can inject into its node metadata.
        """
        if not self._built:
            self.rebuild()
        enrichment: dict[str, Any] = {}
        for mod_name, health in self._health.items():
            ref_count = len(self._xrefs.get(mod_name, []))
            enrichment[mod_name] = {
                "health_score": round(health.health_score, 3),
                "complexity": round(health.complexity_score, 3),
                "dead_fn_count": health.dead_fn_count,
                "cross_ref_count": ref_count,
                "layer": health.layer,
                "critical": health.critical,
            }
        return enrichment

    def to_dict(self) -> dict[str, Any]:
        """Full JSON-safe snapshot of the introspector state."""
        report = self.system_health()
        return {
            "system_health": report.to_dict(),
            "modules": [h.to_dict() for h in self.all_module_health()],
            "knowledge_graph": self.knowledge_graph(),
        }

    def register_update_callback(self, fn: Any) -> None:
        """Register a callable(event_dict) for introspection update events."""
        self._on_update.append(fn)

    # ── Internal analysis methods ─────────────────────────────────────────────

    def _analyze_module(self, path: Path) -> None:
        """Phase 1: Extract metadata from a single module file."""
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        stem = path.stem
        rel_path = str(path.relative_to(_REPO_ROOT))
        lines = source.splitlines()
        line_count = len(lines)

        # Extract classes and functions
        class_names = _RE_CLASS_DEF.findall(source)
        all_fns = _RE_FUNC_DEF.findall(source)
        public_fns = [f for f in all_fns if not f.startswith("_")]
        self._public_fns[stem] = public_fns

        # Count imports from engine
        imports = _RE_FROM_IMPORT.findall(source)
        import_count = len(imports)

        # Track exported symbols (what this module exposes)
        for _, imported_names in imports:
            for name in imported_names.split(","):
                name = name.strip().split(" as ")[0].strip()
                if name:
                    self._exported_symbols[stem].add(name)

        # Compute McCabe-like complexity via AST
        complexity = self._compute_complexity(source, path)

        # Look up knowledge metadata
        knowledge = _MODULE_KNOWLEDGE.get(stem, {})

        self._health[stem] = ModuleHealth(
            module_name=stem,
            file_path=rel_path,
            line_count=line_count,
            class_count=len(class_names),
            function_count=len(all_fns),
            public_fn_count=len(public_fns),
            import_count=import_count,
            complexity_score=complexity,
            layer=knowledge.get("layer", "unknown"),
            critical=knowledge.get("critical", False),
            role=knowledge.get("role", ""),
        )

    def _build_cross_refs(self, path: Path) -> None:
        """Phase 2: Find function-level cross-references from this module."""
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        stem = path.stem
        lines = source.splitlines()

        # Find all `from engine.X import Y, Z` statements
        for match in _RE_FROM_IMPORT.finditer(source):
            target_module = match.group(1)
            imported_names = [
                n.strip().split(" as ")[0].strip()
                for n in match.group(2).split(",")
            ]

            # Now scan the rest of the source for usage of these names
            for i, line in enumerate(lines, 1):
                for name in imported_names:
                    if not name:
                        continue
                    # Check if this imported name appears on this line
                    # (skip the import line itself)
                    if line.strip().startswith(("from ", "import ")):
                        continue
                    if re.search(rf"\b{re.escape(name)}\b", line):
                        # Determine which function we're inside
                        current_fn = self._enclosing_function(lines, i - 1)
                        ref = FunctionRef(
                            source_module=stem,
                            source_fn=current_fn or "<module>",
                            target_module=target_module,
                            target_fn=name,
                            line_no=i,
                        )
                        self._xrefs[target_module].append(ref)
                        self._fn_callers[(target_module, name)].add(stem)

    def _detect_dead_code(self) -> None:
        """Phase 3: Mark public functions with zero external callers."""
        for mod_name, health in self._health.items():
            dead_fns: list[str] = []
            for fn_name in self._public_fns.get(mod_name, []):
                key = (mod_name, fn_name)
                if not self._fn_callers.get(key):
                    dead_fns.append(fn_name)
            health.dead_fn_count = len(dead_fns)
            health.dead_fns = dead_fns

    def _compute_health_scores(self) -> None:
        """Phase 4: Aggregate per-module health scores (0.0-1.0)."""
        if not self._health:
            return

        # Compute dependency depth using CognitiveMap's graph
        self._compute_dependency_depths()

        for mod_name, health in self._health.items():
            score = 1.0

            # Penalty for high complexity (McCabe > 20 is bad)
            if health.complexity_score > 50:
                score -= 0.15
            elif health.complexity_score > 30:
                score -= 0.08
            elif health.complexity_score > 20:
                score -= 0.04

            # Penalty for very large modules (> 800 lines)
            if health.line_count > 1500:
                score -= 0.10
            elif health.line_count > 800:
                score -= 0.05

            # Penalty for dead code (> 10 dead functions)
            dead_ratio = (
                health.dead_fn_count / max(health.public_fn_count, 1)
            )
            if dead_ratio > 0.5:
                score -= 0.10
            elif dead_ratio > 0.3:
                score -= 0.05

            # Penalty for high dependency depth (> 5 levels)
            if health.dependency_depth > 7:
                score -= 0.08
            elif health.dependency_depth > 5:
                score -= 0.04

            # Bonus for being well-referenced (used by many modules)
            if health.dependents_count >= 5:
                score += 0.03
            elif health.dependents_count >= 3:
                score += 0.01

            health.health_score = max(0.0, min(1.0, score))

    def _compute_dependency_depths(self) -> None:
        """Use CognitiveMap's networkx graph for dependency depth analysis."""
        try:
            from engine.cognitive_map import get_cognitive_map
            cmap = get_cognitive_map()
            if cmap._graph is None:
                return

            for mod_name, health in self._health.items():
                node_id = f"engine.{mod_name}"
                if not cmap._graph.has_node(node_id):
                    continue

                # Dependency depth = longest path from this node
                try:
                    paths = dict(
                        cmap._nx.single_source_shortest_path_length(
                            cmap._graph, node_id
                        )
                    )
                    health.dependency_depth = max(
                        paths.values()) if paths else 0
                except Exception:
                    health.dependency_depth = 0

                # Dependents = predecessors (who imports this module)
                try:
                    health.dependents_count = len(
                        list(cmap._graph.predecessors(node_id))
                    )
                except Exception:
                    health.dependents_count = 0

        except Exception:
            logger.debug("CognitiveMap not available for depth analysis")

    @staticmethod
    def _compute_complexity(source: str, path: Path) -> float:
        """Compute McCabe-like cyclomatic complexity via AST."""
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            return 0.0

        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For,
                                 ast.ExceptHandler, ast.With)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # Each and/or adds a branch
                complexity += len(node.values) - 1
            elif isinstance(node, (ast.ListComp, ast.SetComp,
                                   ast.DictComp, ast.GeneratorExp)):
                complexity += 1
        return float(complexity)

    @staticmethod
    def _enclosing_function(lines: list[str], line_idx: int) -> str | None:
        """Walk backwards to find the nearest function definition."""
        for i in range(line_idx, -1, -1):
            stripped = lines[i].lstrip()
            if stripped.startswith("def ") or stripped.startswith("async def "):
                match = _RE_FUNC_DEF.match(stripped)
                if match:
                    return match.group(1)
        return None

    def _build_system_report(self) -> SystemHealthReport:
        """Aggregate all module health into a system report."""
        if not self._health:
            return SystemHealthReport(status="unknown")

        healths = list(self._health.values())
        avg_health = sum(h.health_score for h in healths) / len(healths)
        min_h = min(healths, key=lambda h: h.health_score)

        critical = [h for h in healths if h.critical]
        critical_healthy = sum(1 for h in critical if h.health_score >= 0.7)

        total_dead = sum(h.dead_fn_count for h in healths)
        total_refs = sum(len(refs) for refs in self._xrefs.values())
        total_lines = sum(h.line_count for h in healths)

        # Layer summary
        layer_summary: dict[str, Any] = {}
        for layer in _LAYER_ORDER:
            layer_mods = [h for h in healths if h.layer == layer]
            if layer_mods:
                layer_summary[layer] = {
                    "module_count": len(layer_mods),
                    "avg_health": round(
                        sum(h.health_score for h in layer_mods) /
                        len(layer_mods),
                        3,
                    ),
                    "modules": [h.module_name for h in layer_mods],
                }

        # Traffic light
        if avg_health >= 0.8 and critical_healthy == len(critical):
            status = "green"
        elif avg_health >= 0.6:
            status = "yellow"
        else:
            status = "red"

        # Recommendations
        recs: list[str] = []
        if total_dead > 20:
            recs.append(
                f"High dead code count ({total_dead} functions). "
                "Consider pruning unused public functions."
            )
        if min_h.health_score < 0.6:
            recs.append(
                f"Module '{min_h.module_name}' has low health "
                f"({min_h.health_score:.2f}). Review complexity and deps."
            )
        low_health = [h for h in healths if h.health_score < 0.7]
        if len(low_health) > 3:
            recs.append(
                f"{len(low_health)} modules below 0.7 health threshold. "
                "Consider a targeted refactoring wave."
            )
        if not recs:
            recs.append("System is healthy. No immediate action required.")

        return SystemHealthReport(
            module_count=len(healths),
            avg_health=avg_health,
            min_health_module=min_h.module_name,
            min_health_score=min_h.health_score,
            critical_modules_healthy=critical_healthy,
            critical_modules_total=len(critical),
            total_dead_fns=total_dead,
            total_cross_refs=total_refs,
            total_lines=total_lines,
            layer_summary=layer_summary,
            status=status,
            recommendations=recs,
            built_at=time.time(),
            build_ms=self._build_ts * 1000,
        )

    def _fire_update(self, event: dict[str, Any]) -> None:
        """Notify all registered update callbacks."""
        event.setdefault("type", "deep_introspection_update")
        for fn in list(self._on_update):
            try:
                fn(event)
            except Exception:
                pass


# ── Module-level convenience ──────────────────────────────────────────────────

def get_deep_introspector() -> DeepIntrospector:
    """Convenience accessor — returns the process-level singleton."""
    return DeepIntrospector.get_instance()
