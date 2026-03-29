"""Tests for engine/deep_introspector.py — DeepIntrospector self-awareness engine."""
from __future__ import annotations

import importlib
import threading
from unittest.mock import patch

import pytest


# ── Import smoke ──────────────────────────────────────────────────────────────

def test_import_smoke():
    mod = importlib.import_module("engine.deep_introspector")
    assert hasattr(mod, "DeepIntrospector")
    assert hasattr(mod, "get_deep_introspector")
    assert hasattr(mod, "ModuleHealth")
    assert hasattr(mod, "FunctionRef")
    assert hasattr(mod, "SystemHealthReport")


# ── Singleton is stable ──────────────────────────────────────────────────────

def test_singleton_returns_same_instance():
    from engine.deep_introspector import DeepIntrospector
    a = DeepIntrospector.get_instance()
    b = DeepIntrospector.get_instance()
    assert a is b


def test_get_deep_introspector_convenience():
    from engine.deep_introspector import get_deep_introspector, DeepIntrospector
    di = get_deep_introspector()
    assert isinstance(di, DeepIntrospector)


# ── System health report ────────────────────────────────────────────────────

def test_system_health_returns_report():
    from engine.deep_introspector import get_deep_introspector
    di = get_deep_introspector()
    report = di.system_health()
    assert report.status in ("green", "yellow", "red", "unknown")
    assert report.module_count > 0
    assert 0.0 <= report.avg_health <= 1.0
    assert report.critical_modules_total > 0
    # All critical modules should be healthy in our codebase
    assert report.critical_modules_healthy == report.critical_modules_total
    assert report.total_lines > 0


def test_system_health_to_dict():
    from engine.deep_introspector import get_deep_introspector
    report = get_deep_introspector().system_health()
    d = report.to_dict()
    assert "status" in d
    assert "module_count" in d
    assert "avg_health" in d
    assert "min_health" in d
    assert "critical_modules" in d
    assert "layers" in d
    assert "recommendations" in d
    assert "total_dead_functions" in d
    assert "total_cross_references" in d
    assert "total_lines_of_code" in d


# ── Per-module health ─────────────────────────────────────────────────────────

def test_module_health_known_module():
    from engine.deep_introspector import get_deep_introspector
    di = get_deep_introspector()
    health = di.module_health("router")
    assert health is not None
    assert health.module_name == "router"
    assert health.line_count > 0
    assert health.class_count > 0
    assert 0.0 <= health.health_score <= 1.0
    assert health.layer == "routing"
    assert health.critical is True


def test_module_health_unknown_module():
    from engine.deep_introspector import get_deep_introspector
    assert get_deep_introspector().module_health("nonexistent_xyz") is None


def test_all_module_health_sorted_ascending():
    from engine.deep_introspector import get_deep_introspector
    healths = get_deep_introspector().all_module_health()
    assert len(healths) > 10
    scores = [h.health_score for h in healths]
    assert scores == sorted(scores), "Expected ascending health scores"


def test_module_health_to_dict_keys():
    from engine.deep_introspector import get_deep_introspector
    health = get_deep_introspector().module_health("config")
    assert health is not None
    d = health.to_dict()
    required_keys = {
        "module", "file_path", "line_count", "class_count",
        "function_count", "public_fn_count", "import_count",
        "complexity", "dependency_depth", "dependents_count",
        "dead_fn_count", "dead_fns", "health_score", "layer",
        "critical", "role",
    }
    assert required_keys <= set(d.keys())


# ── Cross-references ──────────────────────────────────────────────────────────

def test_cross_refs_for_config():
    """Config is imported by almost every module — should have many refs."""
    from engine.deep_introspector import get_deep_introspector
    di = get_deep_introspector()
    refs = di.cross_refs("config")
    assert len(refs) > 5, "config should be heavily cross-referenced"
    # Each ref should have the correct target_module
    for ref in refs:
        assert ref.target_module == "config"
        assert ref.source_module != ""
        assert ref.line_no > 0


def test_cross_refs_empty_for_unknown():
    from engine.deep_introspector import get_deep_introspector
    assert get_deep_introspector().cross_refs("totally_fake_module") == []


def test_all_cross_refs_returns_dict():
    from engine.deep_introspector import get_deep_introspector
    all_refs = get_deep_introspector().all_cross_refs()
    assert isinstance(all_refs, dict)
    assert len(all_refs) > 5
    # Each value should be a list of dicts
    for mod, refs in all_refs.items():
        assert isinstance(refs, list)
        if refs:
            assert "source" in refs[0]
            assert "target" in refs[0]


def test_function_ref_to_dict():
    from engine.deep_introspector import FunctionRef
    ref = FunctionRef("router", "route", "config", "settings", 42)
    d = ref.to_dict()
    assert d == {"source": "router.route",
                 "target": "config.settings", "line": 42}


# ── Dead code detection ───────────────────────────────────────────────────────

def test_dead_functions_returns_list():
    from engine.deep_introspector import get_deep_introspector
    dead = get_deep_introspector().dead_functions()
    assert isinstance(dead, list)
    # We should find at least some dead functions (test utilities etc.)
    for item in dead:
        assert "module" in item
        assert "function" in item
        assert "file_path" in item


# ── Knowledge graph ───────────────────────────────────────────────────────────

def test_knowledge_graph_structure():
    from engine.deep_introspector import get_deep_introspector
    kg = get_deep_introspector().knowledge_graph()
    assert "total_modules" in kg
    assert "layers" in kg
    assert "modules" in kg
    assert kg["total_modules"] > 10
    # Layers should be grouped
    assert isinstance(kg["layers"], dict)
    assert "execution" in kg["layers"]
    assert "validation" in kg["layers"]
    assert "core" in kg["layers"]


def test_knowledge_graph_module_entries():
    from engine.deep_introspector import get_deep_introspector
    kg = get_deep_introspector().knowledge_graph()
    for mod in kg["modules"]:
        assert "module" in mod
        assert "role" in mod
        assert "layer" in mod
        assert "critical" in mod
        assert "failsafe" in mod
        assert "health_score" in mod
        assert 0.0 <= mod["health_score"] <= 1.0


# ── Cascade analysis ─────────────────────────────────────────────────────────

def test_cascade_analysis_router():
    from engine.deep_introspector import get_deep_introspector
    di = get_deep_introspector()
    cascade = di.cascade_analysis("engine/router.py")
    assert "source" in cascade
    assert "source_health" in cascade
    assert "affected_count" in cascade
    assert "cascade" in cascade
    assert "max_risk" in cascade
    assert cascade["source_health"] > 0


def test_cascade_analysis_unknown_file():
    from engine.deep_introspector import get_deep_introspector
    cascade = get_deep_introspector().cascade_analysis("engine/nonexistent.py")
    assert cascade["affected_count"] == 0


# ── CognitiveMap enrichment ──────────────────────────────────────────────────

def test_enrich_map_returns_health_data():
    from engine.deep_introspector import get_deep_introspector
    enrichment = get_deep_introspector().enrich_map()
    assert isinstance(enrichment, dict)
    assert len(enrichment) > 10
    for mod, data in enrichment.items():
        assert "health_score" in data
        assert "complexity" in data
        assert "dead_fn_count" in data
        assert "cross_ref_count" in data
        assert "layer" in data
        assert "critical" in data


def test_cognitive_map_to_dict_has_introspection():
    """CognitiveMap.to_dict() should now include introspection data per node."""
    from engine.cognitive_map import get_cognitive_map
    cmap = get_cognitive_map()
    d = cmap.to_dict()
    # At least some nodes should have introspection data
    nodes_with_introspection = [
        n for n in d["nodes"] if "introspection" in n
    ]
    assert len(nodes_with_introspection) > 5, (
        "Expected CognitiveMap nodes to be enriched with introspection data"
    )


# ── Full to_dict snapshot ────────────────────────────────────────────────────

def test_to_dict_full_snapshot():
    from engine.deep_introspector import get_deep_introspector
    d = get_deep_introspector().to_dict()
    assert "system_health" in d
    assert "modules" in d
    assert "knowledge_graph" in d
    assert d["system_health"]["module_count"] > 10
    assert len(d["modules"]) > 10


# ── Rebuild ───────────────────────────────────────────────────────────────────

def test_rebuild_resets_state():
    from engine.deep_introspector import get_deep_introspector
    di = get_deep_introspector()
    count_before = di.system_health().module_count
    di.rebuild()
    count_after = di.system_health().module_count
    assert count_after == count_before, "Rebuild should produce same module count"


# ── Thread safety ──────────────────────────────────────────────────────────────

def test_concurrent_access_no_crash():
    from engine.deep_introspector import get_deep_introspector
    di = get_deep_introspector()
    errors: list[str] = []

    def worker(i: int):
        try:
            if i % 3 == 0:
                di.system_health()
            elif i % 3 == 1:
                di.cross_refs("config")
            else:
                di.module_health("router")
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not errors, f"Concurrent access errors: {errors}"


# ── Update callback ──────────────────────────────────────────────────────────

def test_register_update_callback():
    from engine.deep_introspector import get_deep_introspector
    di = get_deep_introspector()
    events: list[dict] = []
    di.register_update_callback(events.append)
    di.rebuild()
    assert len(events) >= 1
    assert events[-1].get("type") == "deep_introspection_update"
    # Cleanup
    di._on_update.remove(events.append)


# ── Module knowledge coverage ──────────────────────────────────────────────────

def test_critical_modules_have_knowledge():
    """All critical modules should have semantic knowledge entries."""
    from engine.deep_introspector import _MODULE_KNOWLEDGE
    critical = [k for k, v in _MODULE_KNOWLEDGE.items() if v.get("critical")]
    assert len(critical) >= 10, "Expected at least 10 critical modules"
    for mod in critical:
        assert "role" in _MODULE_KNOWLEDGE[mod]
        assert "failsafe" in _MODULE_KNOWLEDGE[mod]
        assert "layer" in _MODULE_KNOWLEDGE[mod]
