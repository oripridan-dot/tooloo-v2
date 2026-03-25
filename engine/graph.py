import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

# Attempt to import configuration variables.
# If `engine.config` or the specific variables are not found,
# they will be assigned default values.
try:
    from engine.config import (
        GRAPH_MAX_NODES_THRESHOLD,
        GRAPH_MAX_RETRIES,
        GRAPH_ROLLBACK_ON_CYCLE,
    )
    _MAX_NODES_THRESHOLD = GRAPH_MAX_NODES_THRESHOLD
    _MAX_RETRIES = GRAPH_MAX_RETRIES
    _ROLLBACK_ON_CYCLE = GRAPH_ROLLBACK_ON_CYCLE
except (ImportError, NameError):
    # Provide default values if config is not available or variables are missing.
    _MAX_NODES_THRESHOLD = 1000
    _MAX_RETRIES = 5
    _ROLLBACK_ON_CYCLE = True


logger = logging.getLogger(__name__)


class CycleDetectedError(ValueError):
    """Raised when adding an edge would violate the DAG invariant by creating a cycle.
    This indicates that the proposed edge connects a node to one of its ancestors,
    breaking the directed acyclic graph property.
    """


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
        # slug → {desc, parent}
        self._events: Dict[str, Dict[str, Optional[str]]] = {}
        self._lock = threading.Lock()

    def record(
        self,
        slug: str,
        description: str,
        caused_by: Optional[str] = None,
    ) -> None:
        if not slug:
            raise ValueError("Event slug cannot be empty or None.")
        with self._lock:
            self._events[slug] = {
                "description": description, "caused_by": caused_by}

    def chain(self, slug: str) -> List[str]:
        """Return the ordered chain [root, …, slug] for a given event slug."""
        with self._lock:
            result: List[str] = []
            current: Optional[str] = slug
            seen: Set[str] = set()
            # FIX 2: Add a maximum depth check for `chain` to prevent infinite loops on malformed data.
            # Use a sensible upper bound, such as the number of events + 1, to detect cycles.
            max_depth = len(self._events) + 1
            depth = 0
            while current and current not in seen and depth < max_depth:
                result.append(current)
                seen.add(current)
                entry = self._events.get(current)
                current = entry["caused_by"] if entry else None
                depth += 1
            if depth >= max_depth:
                logger.warning(f"Provenance chain for '{slug}' exceeded max depth, potential cycle or malformed data.")
            result.reverse()
            return result

    def root_cause(self, slug: str) -> str:
        """Walk parent links back to the root event for `slug`."""
        with self._lock:
            current = slug
            seen: Set[str] = set()
            # FIX 3: Add a maximum depth check for `root_cause` to prevent infinite loops on malformed data.
            # Use a sensible upper bound, such as the number of events + 1, to detect cycles.
            max_depth = len(self._events) + 1
            depth = 0
            while True:
                if current in seen or depth >= max_depth:
                    if depth >= max_depth:
                        logger.warning(f"Root cause search for '{slug}' exceeded max depth, potential cycle or malformed data.")
                    return current
                seen.add(current)
                entry = self._events.get(current)
                parent = entry["caused_by"] if entry else None
                if not parent:
                    return current
                current = parent
                depth += 1


# ── Graph ──────────────────────────────────────────────────────────────────────


class CognitiveGraph:
    """Directed Acyclic Graph of micro-intents.

    Every add_edge() call enforces the DAG invariant immediately.
    A CycleDetectedError is raised and the edge is never committed
    if the addition would create a cycle.

    SLSA/Sigstore note: each node slug maps to a DAG execution step whose
    provenance can be attested via Rekor transparency log entries.  Future
    hardening should hash node outputs and submit attestations so that the
    full execution graph can be independently verified (SLSA Build L3).
    """

    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()
        self._lock = threading.Lock() # Added lock for thread safety

    def add_node(self, slug: str, **attrs: Any) -> None:
        """Adds a node to the graph.

        Args:
            slug: The unique identifier for the node.
            **attrs: Arbitrary attributes to associate with the node.
        """
        with self._lock:
            if len(self._g.nodes) >= _MAX_NODES_THRESHOLD:
                logger.warning(
                    f"Graph size ({len(self._g.nodes)}) reached max threshold "
                    f"({_MAX_NODES_THRESHOLD}). New nodes may be rejected."
                )
            self._g.add_node(slug, **attrs)

    def add_edge(self, source: str, target: str, **attrs: Any) -> None:
        """Add a directed edge from `source` to `target`.

        This method enforces the Directed Acyclic Graph (DAG) invariant. If adding
        the edge would create a cycle, a `CycleDetectedError` is raised, and the
        edge is not added to the graph. This check is performed immediately after
        a tentative edge addition.

        Args:
            source: The slug of the source node.
            target: The slug of the target node.
            **attrs: Additional attributes to associate with the edge.

        Raises:
            CycleDetectedError: If adding the edge would result in a cycle in the graph.
            ValueError: If source or target nodes do not exist in the graph.
        """
        with self._lock:
            if source not in self._g:
                raise ValueError(f"Source node '{source}' not found in graph.")
            if target not in self._g:
                raise ValueError(f"Target node '{target}' not found in graph.")

            # Check for self-loops explicitly
            if source == target:
                raise CycleDetectedError(
                    f"Self-loop detected: Cannot add edge from '{source}' to itself."
                )

            # Optimized cycle detection for adding a single edge.
            # If target is already reachable from source, adding source->target creates a cycle.
            # Equivalently, if source is reachable from target, adding source->target creates a cycle.
            # The check `nx.has_path(self._g, target, source)` is an efficient way to determine
            # if adding `source -> target` would create a back-edge in the existing graph.
            if nx.has_path(self._g, target, source):
                raise CycleDetectedError(
                    f"Cycle detected: Adding edge from '{source}' to '{target}' would create a cycle."
                )

            # If no cycle is detected, add the edge.
            self._g.add_edge(source, target, **attrs)


    def remove_node(self, slug: str) -> None:
        """Removes a node and all incident edges from the graph."""
        with self._lock:
            if slug in self._g:
                self._g.remove_node(slug)
            else:
                logger.warning(f"Node '{slug}' not found in graph for removal.")

    def remove_edge(self, source: str, target: str) -> None:
        """Removes an edge from the graph."""
        with self._lock:
            if self._g.has_edge(source, target):
                self._g.remove_edge(source, target)
            else:
                logger.warning(f"Edge from '{source}' to '{target}' not found in graph for removal.")

    def nodes(self) -> List[str]:
        """Returns a list of all node slugs in the graph."""
        with self._lock:
            return list(self._g.nodes)

    def edges(self) -> List[Tuple[str, str]]:
        """Returns a list of all edges in the graph as (source, target) tuples."""
        with self._lock:
            return list(self._g.edges)

    def has_node(self, slug: str) -> bool:
        """Checks if a node exists in the graph."""
        with self._lock:
            return slug in self._g

    def has_edge(self, source: str, target: str) -> bool:
        """Checks if an edge exists in the graph."""
        with self._lock:
            return self._g.has_edge(source, target)

    @property
    def is_dag(self) -> bool:
        """Checks if the current graph structure is a Directed Acyclic Graph."""
        with self._lock:
            return nx.is_directed_acyclic_graph(self._g)

    def internal(self) -> nx.DiGraph:
        """Returns the internal networkx DiGraph object for advanced operations.

        Caution: Modifying the returned graph directly may bypass safety checks.
        """
        # Return a copy to prevent direct modification and maintain thread safety
        # without locking the entire graph during copy.
        # Note: This creates a deep copy which can be expensive for large graphs.
        # If performance is critical, consider if direct modification is truly needed
        # and if it can be managed with external locking.
        with self._lock:
            return self._g.copy()


# ── Sorter ─────────────────────────────────────────────────────────────────────


class TopologicalSorter:
    """Convert a dependency spec into parallel execution waves.

    Accepts:
      - list[tuple[str, list[str]]]  — (slug, depends_on) pairs
      - CognitiveGraph               — uses predecessor edges

    Raises CycleDetectedError on cycles.
    Returns list[list[str]] — each inner list is a parallel wave.
    """

    def sort(self, spec: Any) -> List[List[str]]:
        entries = self._extract(spec)
        g = nx.DiGraph()
        for slug, deps in entries:
            g.add_node(slug)
            for dep in deps:
                # Ensure dependencies exist as nodes, if not, add them.
                # This handles cases where a dependency might be specified
                # but not explicitly defined as a node in the input spec.
                if dep not in g:
                    g.add_node(dep)
                # Prevent self-loops in the dependency graph
                if dep == slug:
                    raise CycleDetectedError(
                        f"Dependency loop detected: Node '{slug}' depends on itself."
                    )
                g.add_edge(dep, slug)

        if not nx.is_directed_acyclic_graph(g):
            # Perform a more detailed cycle detection and reporting.
            # nx.find_cycle is a good way to identify edges that are part of a cycle.
            try:
                # Get all edges that form cycles. 'orientation' is not directly applicable here.
                # We use 'original' to indicate the directionality of edges in the cycle.
                cycles_edges = list(nx.find_cycle(g, orientation='original'))
                
                if not cycles_edges:
                    # This case might occur if nx.is_directed_acyclic_graph returns False
                    # but find_cycle doesn't return any edges, which is unusual.
                    # We'll report a general cycle detection failure.
                    raise CycleDetectedError(
                        "Cyclic dependency graph — execution halted. Cycle detection found an issue but could not pinpoint edges."
                    )

                # Reconstruct paths for detected cycles for better user feedback.
                cycle_paths: List[str] = []
                
                # Build a mapping of node to its successor within the detected cycle edges.
                # This helps in tracing the cycle path.
                cycle_successors: Dict[str, str] = {}
                involved_nodes_in_any_cycle: Set[str] = set()
                for edge in cycles_edges:
                    u, v = edge[:2]
                    cycle_successors[u] = v
                    involved_nodes_in_any_cycle.add(u)
                    involved_nodes_in_any_cycle.add(v)

                # Iterate through the nodes involved in cycles to find starting points for path reconstruction.
                # Use a set to keep track of nodes already part of a reported cycle to avoid redundant reporting.
                processed_cycle_starts: Set[str] = set() 
                
                # Iterate through all nodes that are part of any detected cycle.
                for start_node in sorted(list(involved_nodes_in_any_cycle)):
                    if start_node in processed_cycle_starts:
                        continue

                    current_node = start_node
                    path_segment: List[str] = []
                    path_nodes_in_current_trace: Set[str] = set() # Track nodes in the current path trace

                    # Trace the cycle path. Add a safeguard for extremely large graphs or malformed cycle data.
                    # The loop should ideally complete within len(g.nodes) iterations for a simple cycle.
                    # Adding a buffer of 2 for safety against complex graph structures or potential off-by-one issues.
                    for _ in range(len(g.nodes) + 2): 
                        if current_node in path_nodes_in_current_trace:
                            # Cycle detected within this trace segment.
                            path_segment.append(current_node) # Close the cycle by appending the node that closes it.
                            cycle_paths.append(" -> ".join(path_segment))
                            processed_cycle_starts.update(path_nodes_in_current_trace) # Mark all nodes in this trace as processed.
                            break
                        
                        path_segment.append(current_node)
                        path_nodes_in_current_trace.add(current_node)

                        if current_node in cycle_successors:
                            next_node = cycle_successors[current_node]
                            current_node = next_node
                        else:
                            # This branch indicates that the current path tracing could not follow a successor.
                            # This might happen if `cycle_successors` doesn't cover all nodes in a cycle due to
                            # how `nx.find_cycle` reports edges, or if the graph structure is very complex.
                            # As a fallback, report all nodes identified as involved in *any* cycle.
                            cycle_paths.append(f"Nodes involved in cycle: {sorted(list(involved_nodes_in_any_cycle))}")
                            processed_cycle_starts.update(involved_nodes_in_any_cycle) # Mark all as processed to avoid redundant reporting.
                            break
                    else:
                        # If the loop completes without breaking, it means we exceeded the expected path length.
                        # This could indicate a non-simple cycle or a graph structure issue.
                        # Report nodes involved in cycles as a fallback.
                        cycle_paths.append(f"Nodes involved in cycle: {sorted(list(involved_nodes_in_any_cycle))}")
                        processed_cycle_starts.update(involved_nodes_in_any_cycle)

                if cycle_paths:
                    # Remove duplicate cycle path strings if any, and sort for consistent output.
                    unique_cycle_paths = sorted(list(set(cycle_paths)))
                    raise CycleDetectedError(
                        f"Cyclic dependency graph — execution halted. Cycles found: {unique_cycle_paths}"
                    )
                else:
                    # If is_directed_acyclic_graph is False and we processed cycles_edges but couldn't form paths,
                    # report a general failure.
                    raise CycleDetectedError(
                        "Cyclic dependency graph — execution halted. Cycle detection failed to reconstruct path."
                    )

            except nx.NetworkXNoCycle:
                # This exception should ideally not be reached if nx.is_directed_acyclic_graph is False,
                # but it serves as a robust fallback for unexpected states.
                raise CycleDetectedError(
                    "Cyclic dependency graph — execution halted. Topological sort failed due to an unexpected cycle state."
                )

        waves: List[List[str]] = []
        remaining: Set[str] = set(g.nodes)
        while remaining:
            # Find nodes in 'remaining' that have no predecessors in 'remaining'.
            # These nodes can be executed in the current wave.
            wave = sorted(
                n for n in remaining
                if all(p not in remaining for p in g.predecessors(n))
            )
            if not wave:
                # If no nodes can be added to the wave, it implies that all remaining nodes have
                # predecessors also among the remaining nodes. This indicates a cycle among the
                # remaining nodes that was not caught by the initial check, or a complex dependency.
                raise CycleDetectedError(
                    "Unresolvable cycle detected among remaining nodes. Topological sort failed."
                )
            waves.append(wave)
            remaining -= set(wave)
        return waves

    def _extract(self, spec: Any) -> List[Tuple[str, List[str]]]:
        if isinstance(spec, CognitiveGraph):
            # Get a copy of the internal graph to avoid modifying the original
            # and to ensure thread-safe access to graph data.
            graph_copy = spec.internal()
            # Extract predecessors for each node to represent dependencies.
            return [(n, list(graph_copy.predecessors(n))) for n in graph_copy.nodes]
        elif isinstance(spec, list):
            if not spec:
                return []
            # Validate the list format: it must be a list of (slug, deps) pairs.
            # Each slug must be a string, and deps must be a list of strings.
            if all(
                isinstance(item, tuple) and len(item) == 2 and
                isinstance(item[0], str) and
                isinstance(item[1], list) and
                all(isinstance(dep, str) for dep in item[1])
                for item in spec
            ):
                # The type hint `List[Tuple[str, List[str]]]` is appropriate here.
                return spec # type: ignore[return-value] # This ignore is a pragmatic choice, as type checkers may struggle with complex `all` conditions.
            else:
                raise TypeError(
                    "When spec is a list, it must be a list of (str, list[str]) tuples where list items are strings."
                )
        else:
            raise TypeError(f"Unsupported spec type: {type(spec)}")
