"""
engine/cognitive_map.py — Live Cognitive Self-Map for TooLoo V2.

Maintains an ever-changing, in-memory networkx DAG of TooLoo's entire codebase
and API surface so the system can act entirely on instinct (cache hits) rather
than re-scanning the workspace on every complex mandate.

Architecture:
  * Every node = one engine module, API endpoint, or key class.
  * Every edge = a dependency (import, calls, belongs-to).
  * Node metadata: file_path, class_names, api_endpoints, intent_tags.
  * Intent-to-node mapping provides instant zero-shot context injection.

Zero-Shot Execution Workflow:
  1. Mandate arrives at NStrokeEngine.
  2. CognitiveMap.relevant_context(intent, mandate_text) → compact blueprint string.
  3. Blueprint injected into make_live_work_fn() as workspace_map.
  4. LLM prompt already knows the exact files and APIs — no grep_search needed.

Thread Safety:
  All mutations (update_node, rebuild) hold ``_lock`` (RLock).
  Reads take no lock for performance; Python GIL protects dict access.

Law 17 Compliance:
  CognitiveMap is a read-heavy singleton.  The build/update path mutates only
  the internal networkx graph and metadata dict — no shared mutable state
  escapes to callers.  All exposed data is returned as immutable copies.
"""
from __future__ import annotations

import logging
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
_STUDIO_ROOT = _REPO_ROOT / "studio"

# ── Intent → primary engine modules (coarse-grained, fast lookup) ─────────────
# Each entry is a list of relative paths from _REPO_ROOT.
_INTENT_MODULE_MAP: dict[str, list[str]] = {
    "BUILD": [
        "engine/pipeline.py", "engine/mandate_executor.py",
        "engine/executor.py", "engine/meta_architect.py",
        "engine/graph.py",
    ],
    "DEBUG": [
        "engine/tribunal.py", "engine/refinement.py",
        "engine/refinement_supervisor.py", "engine/healing_guards.py",
        "engine/psyche_bank.py",
    ],
    "AUDIT": [
        "engine/tribunal.py", "engine/psyche_bank.py",
        "engine/validator_16d.py", "engine/knowledge_banks/manager.py",
        "engine/deep_introspector.py",
    ],
    "DESIGN": [
        "engine/meta_architect.py", "engine/jit_designer.py",
        "engine/knowledge_banks/design_bank.py", "engine/scope_evaluator.py",
    ],
    "EXPLAIN": [
        "engine/conversation.py", "engine/buddy_cognition.py",
        "engine/buddy_memory.py", "engine/router.py",
    ],
    "IDEATE": [
        "engine/meta_architect.py", "engine/jit_booster.py",
        "engine/scope_evaluator.py", "engine/knowledge_banks/bridge_bank.py",
    ],
    "SPAWN_REPO": [
        "engine/mandate_executor.py", "engine/sandbox.py",
        "engine/roadmap.py", "engine/mcp_manager.py",
    ],
    "BLOCKED": [
        "engine/router.py", "engine/refinement_supervisor.py",
        "engine/healing_guards.py", "engine/tribunal.py",
    ],
    "UX_EVAL": [
        "engine/jit_designer.py", "engine/mandate_executor.py",
        "engine/knowledge_banks/design_bank.py", "studio/api.py",
    ],
    "CASUAL": [
        "engine/conversation.py", "engine/buddy_memory.py",
        "engine/buddy_cognition.py", "engine/knowledge_banks/bridge_bank.py",
    ],
    "COACH": [
        "engine/conversation.py", "engine/buddy_cognition.py",
        "engine/knowledge_banks/bridge_bank.py", "engine/knowledge_banks/ai_bank.py",
    ],
    "DISCUSS": [
        "engine/conversation.py", "engine/router.py",
        "engine/knowledge_banks/bridge_bank.py",
    ],
    "PRACTICE": [
        "engine/sandbox.py", "engine/knowledge_banks/code_bank.py",
        "engine/knowledge_banks/ai_bank.py",
    ],
    "SUPPORT": [
        "engine/conversation.py", "engine/buddy_memory.py",
        "engine/knowledge_banks/bridge_bank.py",
    ],
    "UNKNOWN": [
        "engine/router.py", "engine/jit_booster.py",
        "engine/tribunal.py",
    ],
}

# ── Regex patterns for static analysis ───────────────────────────────────────
_RE_ENGINE_IMPORT = re.compile(
    r"^(?:from|import)\s+engine\.(\w[\w.]*)", re.MULTILINE)
_RE_CLASS = re.compile(r"^class\s+(\w+)", re.MULTILINE)
_RE_ASYNC_DEF = re.compile(r"^(?:async\s+)?def\s+(\w+)", re.MULTILINE)
_RE_API_ENDPOINT = re.compile(
    r'@app\.(get|post|put|delete|patch)\(\s*"([^"]+)"', re.MULTILINE)
_RE_SSE_EVENT = re.compile(r'"type":\s*"([a-z_]+)"')


# ── Node metadata dataclass ────────────────────────────────────────────────────

class MapNode:
    """Lightweight metadata container for one graph node."""

    __slots__ = (
        "node_id", "file_path", "module_name", "class_names",
        "public_fns", "api_endpoints", "intent_tags", "last_updated",
    )

    def __init__(
        self,
        node_id: str,
        file_path: str,
        module_name: str,
        class_names: list[str],
        public_fns: list[str],
        api_endpoints: list[str],
        intent_tags: list[str],
    ) -> None:
        self.node_id = node_id
        self.file_path = file_path
        self.module_name = module_name
        self.class_names = class_names
        self.public_fns = public_fns
        self.api_endpoints = api_endpoints
        self.intent_tags = intent_tags
        self.last_updated = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "file_path": self.file_path,
            "module_name": self.module_name,
            "class_names": self.class_names,
            "public_fns": self.public_fns[:10],
            "api_endpoints": self.api_endpoints,
            "intent_tags": self.intent_tags,
            "last_updated": self.last_updated,
        }


# ── Main class ────────────────────────────────────────────────────────────────

class CognitiveMap:
    """
    Ever-changing live DAG of TooLoo's own architecture.

    Usage::

        cmap = CognitiveMap.get_instance()
        # Zero-shot context injection:
        blueprint = cmap.relevant_context("BUILD", "add rate limiting to API")
        # Incremental update after patch:
        cmap.update_node("engine/router.py")
        # Mermaid diagram for SelfImprovementEngine:
        mermaid = cmap.to_mermaid()

    Singleton semantics: ``get_instance()`` returns the same object for the
    lifetime of the process.  Call ``rebuild()`` to force a full re-scan.
    """

    _instance: "CognitiveMap | None" = None
    _instance_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        try:
            import networkx as nx  # type: ignore[import-not-found]
            self._graph: Any = nx.DiGraph()
            self._nx = nx
        except ImportError:  # pragma: no cover
            self._graph = None
            self._nx = None

        self._nodes: dict[str, MapNode] = {}          # node_id → MapNode
        self._intent_index: dict[str, list[str]] = defaultdict(
            list)  # intent → [node_ids]
        self._lock = threading.RLock()
        self._built = False
        self._build_ts: float = 0.0
        # Notify subscribers (api.py broadcast) on any update
        self._on_update: list[Any] = []

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "CognitiveMap":
        """Return the process-level singleton, building it on first call."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    inst = cls()
                    inst.rebuild()
                    cls._instance = inst
        return cls._instance

    # ── Public API ─────────────────────────────────────────────────────────────

    def rebuild(self) -> None:
        """Full workspace rescan — replaces all nodes and edges."""
        t0 = time.monotonic()
        with self._lock:
            if self._graph is not None:
                self._graph.clear()
            self._nodes.clear()
            self._intent_index.clear()

            # Scan engine/ and studio/api.py
            source_files = sorted(_ENGINE_ROOT.rglob("*.py"))
            source_files += [_STUDIO_ROOT / "api.py"]

            for path in source_files:
                if not path.exists():
                    continue
                self._index_file(path)

            self._build_intent_index()
            self._built = True
            self._build_ts = time.monotonic() - t0

        self._fire_update({"event": "rebuild", "node_count": len(self._nodes),
                           "build_ms": round(self._build_ts * 1000, 1)})
        logger.info("CognitiveMap rebuilt: %d nodes in %.1f ms",
                    len(self._nodes), self._build_ts * 1000)

    def update_node(self, file_path: str) -> None:
        """Incremental update — re-parse one file without a full rebuild.

        Called by SelfImprovementEngine and RefinementSupervisor after
        patching any source file.
        """
        abs_path = _REPO_ROOT / file_path
        if not abs_path.exists():
            return
        with self._lock:
            # Remove existing node + edges for this file
            node_id = self._path_to_node_id(abs_path)
            if self._graph is not None and self._graph.has_node(node_id):
                # Remove only edges FROM this node (we'll re-add them)
                out_edges = list(self._graph.out_edges(node_id))
                self._graph.remove_edges_from(out_edges)
            self._nodes.pop(node_id, None)
            # Re-index the file
            self._index_file(abs_path)
            self._build_intent_index()

        self._fire_update(
            {"event": "node_update", "node_id": node_id, "file": file_path})

    def relevant_context(self, intent: str, mandate_text: str = "") -> str:
        """Return a compact workspace blueprint for zero-shot LLM injection.

        The returned string tells the LLM *exactly* which files, classes, and
        API contracts are relevant — eliminating exploratory file reads.

        Format::
            [Workspace Blueprint — <intent>]
            Core files:    engine/pipeline.py, engine/executor.py
            Key classes:   NStrokeEngine, JITExecutor
            API contracts: POST /v2/n-stroke, POST /v2/mandate
            Dep chain:     executor → graph → router → tribunal
        """
        if not self._built:
            self.rebuild()

        node_ids = self._intent_index.get(
            intent, self._intent_index.get("UNKNOWN", []))

        if not node_ids:
            return ""

        files: list[str] = []
        classes: list[str] = []
        endpoints: list[str] = []

        for nid in node_ids[:6]:
            node = self._nodes.get(nid)
            if not node:
                continue
            files.append(node.file_path)
            classes.extend(node.class_names[:3])
            endpoints.extend(node.api_endpoints[:3])

        # Trim dupes while preserving order
        files = list(dict.fromkeys(files))
        classes = list(dict.fromkeys(classes))
        endpoints = list(dict.fromkeys(endpoints))

        # Shortest dep chain between the primary intent nodes (via BFS)
        dep_chain = self._dep_chain(node_ids[:2])

        lines = [f"[Workspace Blueprint — {intent}]"]
        if files:
            lines.append(f"Core files:    {', '.join(files[:5])}")
        if classes:
            lines.append(f"Key classes:   {', '.join(classes[:6])}")
        if endpoints:
            lines.append(f"API contracts: {', '.join(endpoints[:4])}")
        if dep_chain:
            lines.append(f"Dep chain:     {dep_chain}")
        lines.append(
            "INSTRUCTION: Execute directly against the listed files/classes. "
            "No exploratory file_read sweeps required."
        )
        # Inject health context from DeepIntrospector if available
        try:
            from engine.deep_introspector import get_deep_introspector
            di = get_deep_introspector()
            health_lines: list[str] = []
            for nid in node_ids[:4]:
                node = self._nodes.get(nid)
                if not node:
                    continue
                stem = node.module_name.split(".")[-1]
                mh = di.module_health(stem)
                if mh:
                    health_lines.append(
                        f"  {stem}: health={mh.health_score:.2f} "
                        f"complexity={mh.complexity_score:.0f} "
                        f"dead_fns={mh.dead_fn_count}"
                    )
            if health_lines:
                lines.append("Module health:")
                lines.extend(health_lines)
        except Exception:
            pass
        return "\n".join(lines)

    def query_nodes(self, intent: str) -> list[MapNode]:
        """Return MapNode objects for a given intent (for API serialization)."""
        if not self._built:
            self.rebuild()
        nids = self._intent_index.get(intent, [])
        return [self._nodes[nid] for nid in nids if nid in self._nodes]

    def blast_radius(self, file_path: str) -> list[str]:
        """Return a list of file paths that import or depend on ``file_path``.

        Used by RefinementSupervisor to surface which other modules may need
        re-validation after a patch is applied to ``file_path``.
        """
        if not self._built:
            self.rebuild()
        if self._graph is None:
            return []

        # Normalise to the node_id format used internally
        try:
            rel = str(Path(file_path).relative_to(_REPO_ROOT))
        except ValueError:
            rel = file_path
        node_id = rel.replace("/", ".").removesuffix(".py")

        if node_id not in self._graph:
            # Try a fuzzy match — pick any node whose id ends with the stem
            stem = Path(file_path).stem
            candidates = [n for n in self._graph.nodes() if n.endswith(stem)]
            if not candidates:
                return []
            node_id = candidates[0]

        # Predecessors in the dependency graph are callers of this module
        affected: list[str] = []
        try:
            for pred in self._graph.predecessors(node_id):
                node = self._nodes.get(pred)
                if node and node.file_path:
                    affected.append(node.file_path)
        except Exception:
            pass
        return affected

    def to_mermaid(self) -> str:
        """Return a Mermaid graph LR diagram of engine component dependencies."""
        if not self._built:
            self.rebuild()
        if self._graph is None or len(self._nodes) == 0:
            return "```mermaid\ngraph LR\n  TooLoo[TooLoo V2 Engine]\n```"

        lines = ["```mermaid", "graph LR"]
        seen_edges: set[tuple[str, str]] = set()

        # Core engine nodes (abbreviated labels)
        for nid, node in list(self._nodes.items())[:30]:
            label = node.module_name.split(".")[-1]
            lines.append(f"  {_mermaid_id(nid)}[\"{label}\"]")

        if self._graph is not None:
            for src, dst in list(self._graph.edges())[:60]:
                edge = (_mermaid_id(src), _mermaid_id(dst))
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    lines.append(f"  {edge[0]} --> {edge[1]}")

        lines.append("```")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the map to a JSON-safe dict for REST/SSE."""
        nodes_list = [n.to_dict() for n in list(self._nodes.values())[:50]]
        # Enrich with DeepIntrospector health data if available
        try:
            from engine.deep_introspector import get_deep_introspector
            enrichment = get_deep_introspector().enrich_map()
            for nd in nodes_list:
                mod_stem = nd.get("module_name", "").split(".")[-1]
                if mod_stem in enrichment:
                    nd["introspection"] = enrichment[mod_stem]
        except Exception:
            pass
        return {
            "node_count": len(self._nodes),
            "edge_count": self._graph.number_of_edges() if self._graph else 0,
            "built": self._built,
            "build_ms": round(self._build_ts * 1000, 1),
            "nodes": nodes_list,
        }

    def register_update_callback(self, fn: Any) -> None:
        """Register a callable(event_dict) to be notified on map updates."""
        self._on_update.append(fn)

    def node_count(self) -> int:
        return len(self._nodes)

    # ── Internal build helpers ─────────────────────────────────────────────────

    def _index_file(self, path: Path) -> None:
        """Parse one source file and add/update its node + edges in the graph."""
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return

        node_id = self._path_to_node_id(path)
        rel_path = str(path.relative_to(_REPO_ROOT))
        module_name = rel_path.replace("/", ".").removesuffix(".py")

        class_names = _RE_CLASS.findall(source)
        public_fns = [f for f in _RE_ASYNC_DEF.findall(
            source) if not f.startswith("_")]
        api_endpoints = [
            f"{method.upper()} {route}"
            for method, route in _RE_API_ENDPOINT.findall(source)
        ]

        # Determine intent tags from the static map
        intent_tags = [
            intent for intent, paths in _INTENT_MODULE_MAP.items()
            if rel_path in paths
        ]

        node = MapNode(
            node_id=node_id,
            file_path=rel_path,
            module_name=module_name,
            class_names=class_names,
            public_fns=public_fns,
            api_endpoints=api_endpoints,
            intent_tags=intent_tags,
        )
        self._nodes[node_id] = node

        if self._graph is not None:
            self._graph.add_node(node_id, **node.to_dict())

        # Parse imports to build edges
        for match in _RE_ENGINE_IMPORT.finditer(source):
            dep_module = match.group(1).split(".")[0]  # top-level submodule
            dep_id = f"engine.{dep_module}"
            if dep_id != node_id and dep_id in {
                f"engine.{p.stem}" for p in _ENGINE_ROOT.glob("*.py")
            }:
                if self._graph is not None:
                    self._graph.add_edge(node_id, dep_id)

    def _build_intent_index(self) -> None:
        """Map each intent to the pre-configured primary module node IDs."""
        self._intent_index.clear()
        for intent, paths in _INTENT_MODULE_MAP.items():
            node_ids: list[str] = []
            for rel_path in paths:
                abs_path = _REPO_ROOT / rel_path
                nid = self._path_to_node_id(abs_path)
                if nid in self._nodes:
                    node_ids.append(nid)
            self._intent_index[intent] = node_ids

    def _dep_chain(self, start_node_ids: list[str]) -> str:
        """Return a concise dependency chain string using BFS."""
        if not start_node_ids or self._graph is None:
            return ""
        try:
            start = start_node_ids[0]
            if not self._graph.has_node(start):
                return ""
            # BFS up to depth 3
            visited: list[str] = [start]
            queue = [start]
            for _ in range(3):
                next_q: list[str] = []
                for nid in queue:
                    for _, nbr in self._graph.out_edges(nid):
                        if nbr not in visited:
                            visited.append(nbr)
                            next_q.append(nbr)
                queue = next_q[:3]
                if not queue:
                    break
            labels = [
                self._nodes[nid].module_name.split(".")[-1]
                for nid in visited[:5]
                if nid in self._nodes
            ]
            return " → ".join(labels)
        except Exception:
            return ""

    @staticmethod
    def _path_to_node_id(path: Path) -> str:
        """Convert an absolute path to a stable dot-separated node ID."""
        try:
            rel = path.relative_to(_REPO_ROOT)
        except ValueError:
            rel = path
        return str(rel).replace("/", ".").replace("\\", ".").removesuffix(".py")

    def _fire_update(self, event: dict[str, Any]) -> None:
        """Notify all registered update callbacks (e.g. SSE broadcast)."""
        event.setdefault("type", "self_map_update")
        for fn in list(self._on_update):
            try:
                fn(event)
            except Exception:
                pass


# ── Helpers ────────────────────────────────────────────────────────────────────

def _mermaid_id(node_id: str) -> str:
    """Sanitise a node ID to a valid Mermaid node identifier."""
    return re.sub(r"[^a-zA-Z0-9_]", "_", node_id)


def get_cognitive_map() -> CognitiveMap:
    """Convenience accessor — returns the process-level singleton."""
    return CognitiveMap.get_instance()
