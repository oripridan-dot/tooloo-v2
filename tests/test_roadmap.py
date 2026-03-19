"""Tests for engine/roadmap.py — RoadmapManager and RoadmapItem."""
from __future__ import annotations

from engine.roadmap import RoadmapItem, RoadmapManager


class TestRoadmapManagerBaseline:
    def test_initial_seeded_items(self):
        rm = RoadmapManager()
        items = rm.all_items()
        # Built-in roadmap has 10 seed items
        assert len(items) >= 10

    def test_add_item_returns_roadmap_item(self):
        rm = RoadmapManager()
        item = rm.add_item(
            title="OAuth2 provider integration",
            description="Integrate OAuth2 provider for third-party login support",
        )
        assert item is not None
        assert isinstance(item, RoadmapItem)

    def test_add_item_id_is_assigned(self):
        rm = RoadmapManager()
        item = rm.add_item(
            title="Rate-limit middleware",
            description="Add per-user rate limiting via Redis sliding window",
        )
        assert item is not None
        assert item.id.startswith("RM-")

    def test_add_item_custom_id(self):
        rm = RoadmapManager()
        result = rm.add_item(
            title="Feature flag service",
            description="LaunchDarkly-style feature flag evaluation engine",
            item_id="RM-TEST-001",
        )
        assert result is not None
        assert result.id == "RM-TEST-001"

    def test_add_item_with_priority(self):
        rm = RoadmapManager()
        item = rm.add_item(
            title="Database connection pooling",
            description="PgBouncer-backed connection pool for high concurrency",
            priority="critical",
        )
        assert item is not None
        assert item.priority == "critical"

    def test_get_item_by_id(self):
        rm = RoadmapManager()
        rm.add_item(
            title="Async job queue",
            description="Celery-backed async task queue for background processing",
            item_id="RM-Q-001",
        )
        fetched = rm.get_item("RM-Q-001")
        assert fetched is not None
        assert fetched.title == "Async job queue"

    def test_get_report_returns_correct_structure(self):
        rm = RoadmapManager()
        report = rm.get_report()
        assert report.total_items >= 10
        assert report.wave_count >= 1
        assert isinstance(report.waves, list)

    def test_waves_are_non_empty(self):
        rm = RoadmapManager()
        waves = rm.waves()
        assert len(waves) >= 1

    def test_find_similar_returns_results(self):
        rm = RoadmapManager()
        results = rm.find_similar("vector similarity deduplication")
        assert isinstance(results, list)


class TestRoadmapSemanticDeduplication:
    def test_exact_duplicate_rejected(self):
        rm = RoadmapManager()
        item1 = rm.add_item(
            title="WebSocket real-time events",
            description="WebSocket real-time event broadcasting for live updates",
            item_id="RM-WS-001",
        )
        assert item1 is not None
        # Exact same text → near-duplicate, must return None
        item2 = rm.add_item(
            title="WebSocket real-time events",
            description="WebSocket real-time event broadcasting for live updates",
            item_id="RM-WS-002",
        )
        assert item2 is None, "Exact duplicate should be rejected by VectorStore"

    def test_distinct_items_both_accepted(self):
        rm = RoadmapManager()
        item_a = rm.add_item(
            title="Email notification service",
            description="SMTP-based email notifications for user alerts",
            item_id="RM-EMAIL-001",
        )
        item_b = rm.add_item(
            title="CI/CD pipeline automation",
            description="GitHub Actions-based continuous integration and deployment",
            item_id="RM-CICD-001",
        )
        # Both are semantically distinct — both should be accepted
        assert item_a is not None
        assert item_b is not None
