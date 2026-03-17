"""
engine/graph.py — Pure DAG logic. No LLM, no network, no I/O.

CycleDetectedError         — Raised when a cycle would be introduced.
ProvenanceEdge             — One backward causal link.
CausalProvenanceTracker    — Thread-safe causal chain recorder.
CognitiveGraph             — Enforced DAG (networkx DiGraph).
TopologicalSorter          — Parallel-wave sorter that hard-rejects cycles.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any

import networkx as nx


class CycleDetectedError(ValueError):
    """Raised when adding an edge would violate the DAG invariant."""


# ── Provenance ─────────────────────────────────────────────────────────────────


@dataclass
class ProvenanceEdge:
    source: str
    target: str
    edge_type: str = "CAUSES"


class CausalProvenanceTracker:
    """Thread-safe event recorder with parent-link provenance chains.

    record(slug, description, caused_by=None)  — log an event
    chain(slug)     → list[str] of slugs from root → slug
    root_cause(slug) → root slug (or slug itself if no parent)
    """

    def __init__(self) -> None:
        self._events: dict[str, dict[str, str | None]] = {}  # slug → {desc, parent}
        self._lock = threading.Lock()

    def record(
        self,
        slug: str,
        description: str,
        caused_by: str | None = None,
    ) -> None:
        with self._lock:
            self._events[slug] = {"description": description, "caused_by": caused_by}

    def chain(self, slug: str) -> list[str]:
        """Return the ordered chain [root, …, slug] for a given event slug."""
        with self._lock:
            result: list[str] = []
            current: str | None = slug
            seen: set[str] = set()
            while current and current not in seen:
                result.append(current)
                seen.add(current)
                entry = self._events.get(current)
                current = entry["caused_by"] if entry else None
            result.reverse()
            return result

    def root_cause(self, slug: str) -> str:
        """Walk parent links back to the root event for `slug`."""
        with self._lock:
            current = slug
            seen: set[str] = set()
            while True:
                if current in seen:
                    return current
                seen.add(current)
                entry = self._events.get(current)
                parent = entry["caused_by"] if entry else None
                if not parent:
                    return current
                current = parent


# ── Graph ──────────────────────────────────────────────────────────────────────


class CognitiveGraph:
    """Directed Acyclic Graph of micro-intents.

    Every add_edge() call enforces the DAG invariant immediately.
    A CycleDetectedError is raised and the edge is never committed
    if the addition would create a cycle.
    """

    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()

    def add_node(self, slug: str, **attrs: Any) -> None:
        self._g.add_node(slug, **attrs)

    def add_edge(self, source: str, target: str, **attrs: Any) -> None:
        self._g.add_edge(source, target, **attrs)
        if not nx.is_directed_acyclic_graph(self._g):
            self._g.remove_edge(source, target)
            raise CycleDetectedError(
                f"Cycle detected: {source!r} → {target!r} violates the DAG invariant."
            )

    def nodes(self) -> list[str]:
        return list(self._g.nodes)

    def edges(self) -> list[tuple[str, str]]:
        return list(self._g.edges)

    @property
    def is_dag(self) -> bool:
        return nx.is_directed_acyclic_graph(self._g)

    def internal(self) -> nx.DiGraph:
        return self._g


# ── Sorter ─────────────────────────────────────────────────────────────────────


class TopologicalSorter:
    """Convert a dependency spec into parallel execution waves.

    Accepts:
      - list[tuple[str, list[str]]]  — (slug, depends_on) pairs
      - CognitiveGraph               — uses predecessor edges

    Raises CycleDetectedError on cycles.
    Returns list[list[str]] — each inner list is a parallel wave.
    """

    def sort(self, spec: Any) -> list[list[str]]:
        entries = self._extract(spec)
        g = nx.DiGraph()
        for slug, deps in entries:
            g.add_node(slug)
            for dep in deps:
                g.add_edge(dep, slug)

        if not nx.is_directed_acyclic_graph(g):
            raise CycleDetectedError("Cyclic dependency graph — execution halted.")

        waves: list[list[str]] = []
        remaining = set(g.nodes)
        while remaining:
            wave = sorted(
                n for n in remaining
                if all(p not in remaining for p in g.predecessors(n))
            )
            if not wave:
                raise CycleDetectedError("Unresolvable cycle across remaining nodes.")
            waves.append(wave)
            remaining -= set(wave)
        return waves

    def _extract(self, spec: Any) -> list[tuple[str, list[str]]]:
        if isinstance(spec, CognitiveGraph):
            g = spec.internal()
            return [(n, list(g.predecessors(n))) for n in g.nodes]
        if isinstance(spec, list) and spec and isinstance(spec[0], tuple):
            return spec  # type: ignore[return-value]
        raise TypeError(f"Unsupported spec type: {type(spec)}")
