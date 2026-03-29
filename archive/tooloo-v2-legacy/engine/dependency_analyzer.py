# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.dependency_analyzer.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

"""
engine/dependency_analyzer.py - Concrete Dependency Graph Analyzer

This module provides tools to build and query a dependency graph of the
workspace. It is used to power the "Cascade Preview" by identifying which
files will be impacted by a change to a specific file.

The analyzer parses Python files to find import statements and builds a
directed graph representing the dependencies.
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path

import networkx as nx

from engine.config import get_workspace_roots

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """
    Builds and queries a file-level dependency graph for the workspace.
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self._workspace_roots = get_workspace_roots()

    def build_graph_from_workspace(self, file_extensions: tuple = (".py",)) -> None:
        """
        Scans all workspace roots for Python files and builds the dependency graph.
        """
        logger.info("Building workspace dependency graph...")
        py_files = []
        for root in self._workspace_roots:
            for ext in file_extensions:
                for p in Path(root).rglob(f"*{ext}"):
                    if ".venv" not in p.parts and ".git" not in p.parts:
                        py_files.append(p)

        for file_path in py_files:
            self._add_node_and_dependencies(file_path)

        logger.info(
            f"Dependency graph built with {self.graph.number_of_nodes()} nodes "
            f"and {self.graph.number_of_edges()} edges."
        )

    def _add_node_and_dependencies(self, file_path: Path) -> None:
        """
        Adds a single file to the graph and parses its imports to add edges.
        """
        try:
            # Normalize the node path to be relative to a workspace root
            node_path_str = self._normalize_path(file_path)
            if not node_path_str:
                return
            
            self.graph.add_node(node_path_str)

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._add_edge_from_module_name(node_path_str, alias.name, file_path.parent)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self._add_edge_from_module_name(node_path_str, node.module, file_path.parent)

        except Exception as e:
            logger.warning(f"Could not parse dependencies for {file_path}: {e}")

    def _add_edge_from_module_name(self, source_node: str, module_name: str, current_dir: Path):
        """
        Resolves a module name to a file path and adds a dependency edge.
        """
        # This is a simplified resolver. A real implementation would need to handle
        # sys.path, packages vs. modules, relative imports more robustly.
        try:
            # Attempt to resolve relative imports (e.g., `from . import foo`)
            if module_name.startswith('.'):
                 # simplistic relative import handling
                base = current_dir
                level = 0
                while module_name.startswith('.'):
                    level += 1
                    module_name = module_name[1:]
                
                if level > 1:
                    base = current_dir.parents[level-2]
                
                if not module_name: # e.g. from . import X
                    candidate = base / "__init__.py"
                else:
                    candidate = base / f"{module_name.replace('.', '/')}.py"

            else: # Absolute import
                # Find the root for this absolute import
                for root in self._workspace_roots:
                    candidate = root / f"{module_name.replace('.', '/')}.py"
                    if candidate.exists():
                        break
                    candidate = root / module_name.replace('.', '/') / "__init__.py"
                    if candidate.exists():
                        break
                else:
                    return # Could not find module in any workspace root

            if candidate.exists():
                dep_node_str = self._normalize_path(candidate)
                if dep_node_str and self.graph.has_node(dep_node_str):
                    self.graph.add_edge(source_node, dep_node_str)

        except Exception:
            # Fail silently if a module can't be resolved.
            pass

    def get_downstream_dependencies(self, file_path: str | Path) -> dict[str, list[str]]:
        """
        Finds all nodes that are dependent on the given file (the "cascade").

        Args:
            file_path: The path of the file to start from.

        Returns:
            A dictionary representing the subgraph of downstream dependencies.
            { "nodes": ["node1", "node2"], "edges": [["node1", "node2"]] }
        """
        try:
            start_node = self._normalize_path(file_path)
            if not start_node or not self.graph.has_node(start_node):
                return {"nodes": [], "edges": []}

            # We need the reverse graph to find what depends ON the start_node
            reverse_graph = self.graph.reverse(copy=True)
            
            # Find all nodes reachable from the start_node in the reversed graph
            downstream_nodes = nx.descendants(reverse_graph, start_node)
            downstream_nodes.add(start_node)

            subgraph = self.graph.subgraph(downstream_nodes)

            return {
                "nodes": list(subgraph.nodes),
                "edges": [list(edge) for edge in subgraph.edges]
            }
        except Exception as e:
            logger.error(f"Error getting downstream dependencies for {file_path}: {e}")
            return {"nodes": [], "edges": []}
            
    def _normalize_path(self, path: str | Path) -> str | None:
        """
        Normalizes a path to be relative to one of the workspace roots.
        """
        p = Path(path).resolve()
        for root in self._workspace_roots:
            try:
                relative_path = p.relative_to(root)
                return str(relative_path)
            except ValueError:
                continue
        return None

if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)
    analyzer = DependencyAnalyzer()
    analyzer.build_graph_from_workspace()
    
    # Find what would be affected by a change in the router
    if "engine/router.py" in analyzer.graph:
        cascade = analyzer.get_downstream_dependencies("engine/router.py")
        print("\nCascade preview for changing engine/router.py:")
        print(cascade)
    else:
        print("engine/router.py not found in graph.")