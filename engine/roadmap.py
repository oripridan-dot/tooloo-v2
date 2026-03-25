"""
engine/roadmap.py — Graph-backed roadmap manager.

The system roadmap lives as a DAG (CognitiveGraph). Each node is a feature/goal
with metadata: priority, impact, status, sandbox linkage.

TopologicalSorter produces execution waves — which features can run in parallel.
VectorStore indexes every description for semantic clustering and near-duplicate
rejection (threshold 0.88 — slightly more permissive than sandbox dedup).

Built-in roadmap: the 7 core system goals + 3 architectural suggestions (10 items).
All state is in-memory; mutations are thread-safe via RLock.

Public API:
  RoadmapManager.add_item(...)           → RoadmapItem | None
  RoadmapManager.update_item_scores(...) → bool
  RoadmapManager.waves()                 → list[list[str]]
  RoadmapManager.find_similar(query)     → list[dict]
  RoadmapManager.get_report()            → RoadmapReport
  RoadmapManager.all_items()             → list[RoadmapItem]
"""
from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from engine.graph import CognitiveGraph, TopologicalSorter
from engine.vector_store import VectorStore

# ── Item statuses ─────────────────────────────────────────────────────────────
STATUS_QUEUED = "queued"
STATUS_SANDBOX = "sandbox"
STATUS_PROVEN = "proven"
STATUS_PROMOTED = "promoted"
STATUS_BLOCKED = "blocked"
STATUS_FAILED = "failed"

_PRIORITY_RANK: dict[str, int] = {
    "critical": 0, "high": 1, "medium": 2, "low": 3,
}

_ALL_DIMENSIONS: list[str] = [
    "legal", "safety", "security", "accuracy", "honesty",
    "efficiency", "quality", "performance", "time_awareness",
]

# ── Built-in roadmap ──────────────────────────────────────────────────────────
# Wave 1 (no deps) → Wave 2 (dep on W1) → Wave 3 (dep on W2) → Wave 4 (dep on W3)
_INITIAL_ITEMS: list[dict[str, Any]] = [
    # ── Wave 1: Foundation — no dependencies ─────────────────────────────────
    {
        "id": "RM-001",
        "title": "Intent-Adaptive Response Engine",
        "description": (
            "Seek, find and refine the best ways on responding, planning and executing "
            "in order to aid users manifest their intents. Continuous improvement of "
            "routing accuracy and response quality through multi-path evaluation and "
            "graph-backed learning cycles."
        ),
        "priority": "critical",
        "deps": [],
        "evaluation_dimensions": _ALL_DIMENSIONS,
    },
    {
        "id": "RM-002",
        "title": "Multi-Dimensional Process Evaluator",
        "description": (
            "Every process must consider: legal, safety, security, accuracy, honesty, "
            "efficiency, quality, performance, time awareness — all preferred over speed. "
            "Embed a 9-dimension scoring rubric into every execution node and sandbox run."
        ),
        "priority": "critical",
        "deps": [],
        "evaluation_dimensions": _ALL_DIMENSIONS,
    },
    # ── Wave 2: Core capabilities — depend on Wave 1 ─────────────────────────
    {
        "id": "RM-003",
        "title": "Dynamic Scope-Target Adjuster",
        "description": (
            "Consider task scope and target and adjust the process on the fly. "
            "Real-time re-planning as context shifts, scope narrows, or priority changes. "
            "DAG node replanning without full pipeline restart."
        ),
        "priority": "high",
        "deps": ["RM-001"],
        "evaluation_dimensions": ["accuracy", "efficiency", "performance", "time_awareness"],
    },
    {
        "id": "RM-004",
        "title": "Human Cognition and Behavior Layer",
        "description": (
            "Human behavior and cognition addressing as mandatory consideration for "
            "all human-facing processes. Adapt tone, pacing, complexity, and framing "
            "to cognitive load, expertise level, emotional context, and intent clarity."
        ),
        "priority": "high",
        "deps": ["RM-001"],
        "evaluation_dimensions": ["honesty", "accuracy", "quality", "safety"],
    },
    {
        "id": "RM-005",
        "title": "Google Cloud and Vertex AI Integration",
        "description": (
            "Use Google Cloud and Vertex AI optimally: Vertex Agent Builder, "
            "Gemini 2.x model garden, gemini-embedding-001 for vector operations, "
            "Vertex AI Pipelines for orchestration, Cloud Spanner for graph queries."
        ),
        "priority": "high",
        "deps": ["RM-002"],
        "evaluation_dimensions": ["efficiency", "performance", "quality", "security"],
    },
    {
        "id": "RM-009",
        "title": "Vector-Similarity Feature Deduplication",
        "description": (
            "Use TF-IDF plus cosine similarity vectors to detect and merge duplicate "
            "or conflicting features before spawning sandboxes. Prevents redundant "
            "work and ensures the roadmap stays coherent and non-contradictory."
        ),
        "priority": "medium",
        "deps": ["RM-002"],
        "evaluation_dimensions": ["efficiency", "quality", "time_awareness"],
    },
    # ── Wave 3: Evolution layer — depend on Wave 2 ───────────────────────────
    {
        "id": "RM-006",
        "title": "Ever-Evolving State Machine",
        "description": (
            "Make the ever-evolving state the default and make it solid. "
            "Every executed mandate updates the system state graph. "
            "Persistent learning loop: sandbox results feed psyche_bank automatically."
        ),
        "priority": "critical",
        "deps": ["RM-002", "RM-003"],
        "evaluation_dimensions": ["quality", "performance", "efficiency", "security"],
    },
    {
        "id": "RM-007",
        "title": "Simple Yet Impactful Workflow Logic",
        "description": (
            "Keep the workflow logic simple yet impactful. Reduce node count where "
            "possible, eliminate redundant hops, ensure each wave adds clear value. "
            "Complexity budget: max 7 nodes per mandate wave."
        ),
        "priority": "high",
        "deps": ["RM-003", "RM-004"],
        "evaluation_dimensions": ["efficiency", "quality", "time_awareness"],
    },
    # ── Wave 4: Advanced capabilities — depend on Wave 3 ─────────────────────
    {
        "id": "RM-008",
        "title": "Persistent Cross-Session Memory Graph",
        "description": (
            "Graph-backed memory that persists insights, patterns, and decisions "
            "across sessions. Enables true continuity of context: past sandbox "
            "results inform future routing, scope evaluation, and tribunal rules."
        ),
        "priority": "high",
        "deps": ["RM-006"],
        "evaluation_dimensions": ["accuracy", "quality", "security", "honesty"],
    },
    {
        "id": "RM-010",
        "title": "Parallel Sandbox Promotion Pipeline",
        "description": (
            "Proven sandbox results auto-promote to main pipeline with confidence "
            "gates (readiness_score at least 0.72) and rollback capability. "
            "Supervised by RefinementLoop with up to 25 concurrent promotions."
        ),
        "priority": "high",
        "deps": ["RM-006", "RM-007"],
        "evaluation_dimensions": _ALL_DIMENSIONS,
    },
]


# ── DTOs ──────────────────────────────────────────────────────────────────────

@dataclass
class RoadmapItem:
    id: str
    title: str
    description: str
    priority: str               # critical | high | medium | low
    deps: list[str]
    status: str = STATUS_QUEUED
    sandbox_id: str | None = None
    impact_score: float = 0.0
    difficulty_score: float = 0.0
    readiness_score: float = 0.0
    timeline_days: int = 0
    evaluation_dimensions: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat())
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "deps": self.deps,
            "status": self.status,
            "sandbox_id": self.sandbox_id,
            "impact_score": round(self.impact_score, 3),
            "difficulty_score": round(self.difficulty_score, 3),
            "readiness_score": round(self.readiness_score, 3),
            "timeline_days": self.timeline_days,
            "evaluation_dimensions": self.evaluation_dimensions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "notes": self.notes,
        }


@dataclass
class RoadmapReport:
    total_items: int
    waves: list[list[str]]
    by_status: dict[str, int]
    by_priority: dict[str, int]
    wave_count: int
    max_parallel: int
    items: list[RoadmapItem]
    generated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_items": self.total_items,
            "waves": self.waves,
            "by_status": self.by_status,
            "by_priority": self.by_priority,
            "wave_count": self.wave_count,
            "max_parallel": self.max_parallel,
            "items": [i.to_dict() for i in self.items],
            "generated_at": self.generated_at,
        }


# ── Manager ───────────────────────────────────────────────────────────────────

class RoadmapManager:
    """Graph-backed roadmap manager.

    Items live as nodes in a CognitiveGraph (DAG).
    TopologicalSorter provides execution wave plans.
    VectorStore indexes descriptions for clustering and duplicate detection.
    """

    def __init__(self) -> None:
        self._graph = CognitiveGraph()
        self._sorter = TopologicalSorter()
        # lowered: reject only near-identical items
        self._vector_store = VectorStore(dup_threshold=0.70)
        self._items: dict[str, RoadmapItem] = {}
        self._lock = threading.RLock()
        self._seed_initial()

    def _seed_initial(self) -> None:
        for raw in _INITIAL_ITEMS:
            self.add_item(
                item_id=raw["id"],
                title=raw["title"],
                description=raw["description"],
                priority=raw["priority"],
                deps=raw["deps"],
                evaluation_dimensions=raw.get("evaluation_dimensions", []),
            )

    def add_item(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        deps: list[str] | None = None,
        item_id: str | None = None,
        evaluation_dimensions: list[str] | None = None,
    ) -> RoadmapItem | None:
        """Add a roadmap item. Returns None if near-duplicate detected."""
        with self._lock:
            deps = deps or []
            item_id = item_id or f"RM-{uuid.uuid4().hex[:6].upper()}"
            is_new = self._vector_store.add(
                doc_id=item_id,
                text=f"{title} {description}",
                metadata={"item_id": item_id,
                          "title": title, "priority": priority},
            )
            if not is_new:
                return None  # near-duplicate — rejected

            item = RoadmapItem(
                id=item_id,
                title=title,
                description=description,
                priority=priority,
                deps=deps,
                evaluation_dimensions=evaluation_dimensions or list(
                    _ALL_DIMENSIONS),
            )
            self._items[item_id] = item
            self._graph.add_node(item_id)
            for dep in deps:
                if dep in self._items:
                    self._graph.add_edge(dep, item_id)
            return item

    def get_item(self, item_id: str) -> RoadmapItem | None:
        with self._lock:
            return self._items.get(item_id)

    def update_item_scores(
        self,
        item_id: str,
        impact_score: float,
        difficulty_score: float,
        readiness_score: float,
        timeline_days: int,
        status: str | None = None,
        sandbox_id: str | None = None,
        notes: list[str] | None = None,
    ) -> bool:
        with self._lock:
            item = self._items.get(item_id)
            if not item:
                return False
            item.impact_score = impact_score
            item.difficulty_score = difficulty_score
            item.readiness_score = readiness_score
            item.timeline_days = timeline_days
            item.updated_at = datetime.now(UTC).isoformat()
            if status:
                item.status = status
            if sandbox_id:
                item.sandbox_id = sandbox_id
            if notes:
                item.notes.extend(notes)
            return True

    def waves(self) -> list[list[str]]:
        """Return topological execution waves for the full roadmap DAG."""
        with self._lock:
            if not self._items:
                return []
            spec = [(iid, list(item.deps))
                    for iid, item in self._items.items()]
            return self._sorter.sort(spec)

    def find_similar(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """Find roadmap items most semantically similar to query."""
        results = self._vector_store.search(query, top_k=top_k, threshold=0.1)
        return [
            {**r.to_dict(), "item": self._items[r.id].to_dict()}
            for r in results
            if r.id in self._items
        ]

    def get_report(self) -> RoadmapReport:
        with self._lock:
            items = list(self._items.values())
            waves_data = self.waves()
            by_status: dict[str, int] = {}
            by_priority: dict[str, int] = {}
            for item in items:
                by_status[item.status] = by_status.get(item.status, 0) + 1
                by_priority[item.priority] = by_priority.get(
                    item.priority, 0) + 1
            max_parallel = max((len(w) for w in waves_data), default=0)
            return RoadmapReport(
                total_items=len(items),
                waves=waves_data,
                by_status=by_status,
                by_priority=by_priority,
                wave_count=len(waves_data),
                max_parallel=max_parallel,
                items=sorted(
                    items,
                    key=lambda x: (_PRIORITY_RANK.get(x.priority, 99), x.id),
                ),
            )

    def all_items(self) -> list[RoadmapItem]:
        with self._lock:
            return list(self._items.values())

    def vector_store_summary(self) -> dict[str, Any]:
        return self._vector_store.to_dict()
