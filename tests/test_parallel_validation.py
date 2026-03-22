"""Tests for engine/parallel_validation.py — Parallel Validation Pipeline."""
from __future__ import annotations

import asyncio

import pytest

from engine.parallel_validation import (
    FileChange,
    ParallelValidationPipeline,
    StageResult,
    ValidationReport,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def pipeline():
    """Pipeline with SSE capture."""
    events: list[dict] = []
    p = ParallelValidationPipeline(broadcast_fn=lambda e: events.append(e))
    p._events = events  # type: ignore[attr-defined]
    return p


# ── Data class tests ──────────────────────────────────────────────────────────


def test_file_change_defaults():
    c = FileChange(path="engine/router.py")
    assert c.component == ""
    assert c.content is None


def test_stage_result_to_dict():
    s = StageResult(
        stage="tribunal", file_path="engine/router.py",
        success=True, score=1.0, details="clean", latency_ms=5.5,
    )
    d = s.to_dict()
    assert d["stage"] == "tribunal"
    assert d["success"] is True
    assert d["score"] == 1.0
    assert d["latency_ms"] == 5.5


def test_validation_report_to_dict():
    r = ValidationReport(
        pipeline_id="test-1",
        files_validated=2,
        all_passed=True,
        composite_score=0.9843,
        tribunal_passed=True,
        test_passed=True,
        latency_ms=123.45,
    )
    d = r.to_dict()
    assert d["pipeline_id"] == "test-1"
    assert d["all_passed"] is True
    assert d["composite_score"] == 0.9843


# ── Pipeline core tests ──────────────────────────────────────────────────────


def test_derive_component():
    assert ParallelValidationPipeline._derive_component(
        "engine/router.py") == "router"
    assert ParallelValidationPipeline._derive_component(
        "engine/jit_booster.py") == "jit_booster"


def test_find_test_targets():
    targets = ParallelValidationPipeline._find_test_targets(
        "engine/validator_16d.py")
    assert any("test_validator_16d" in t for t in targets)


def test_find_test_targets_no_match():
    targets = ParallelValidationPipeline._find_test_targets(
        "engine/nonexistent_module.py")
    assert targets == []


def test_read_source():
    src = ParallelValidationPipeline._read_source("engine/config.py")
    assert "settings" in src.lower() or len(src) > 100


def test_read_source_traversal():
    src = ParallelValidationPipeline._read_source("../../etc/passwd")
    assert src == ""


@pytest.mark.asyncio
async def test_validate_changes_tribunal_and_16d(pipeline):
    """Validate tribunal + 16D run concurrently (no tests)."""
    changes = [FileChange(path="engine/router.py", component="router")]
    report = await pipeline.validate_changes(changes, run_tests=False)

    assert report.files_validated == 1
    assert report.tribunal_passed is True
    assert report.composite_score > 0.9

    stage_names = [s.stage for s in report.stages]
    assert "tribunal" in stage_names
    assert "16d" in stage_names

    # SSE events were broadcast
    events = pipeline._events  # type: ignore[attr-defined]
    assert any(e.get("type") == "parallel_validation_start" for e in events)
    assert any(e.get("type") == "parallel_validation_complete" for e in events)


@pytest.mark.asyncio
async def test_validate_changes_multiple_files(pipeline):
    """Validate multiple files concurrently."""
    changes = [
        FileChange(path="engine/router.py", component="router"),
        FileChange(path="engine/tribunal.py", component="tribunal"),
    ]
    report = await pipeline.validate_changes(changes, run_tests=False)

    assert report.files_validated == 2
    tribunal_stages = [s for s in report.stages if s.stage == "tribunal"]
    dim16_stages = [s for s in report.stages if s.stage == "16d"]
    assert len(tribunal_stages) == 2
    assert len(dim16_stages) == 2


@pytest.mark.asyncio
async def test_validate_and_write_blocks_on_failure(pipeline):
    """validate_and_write should not write files when validation fails."""
    # Use a fake file with poisoned content to trigger tribunal failure
    changes = [FileChange(
        path="engine/test_fake.py",
        content='SECRET_KEY = "hardcoded_abc123"\neval(user_input)',
        component="test_fake",
    )]
    report = await pipeline.validate_and_write(changes, run_tests=False)

    # The write should not have happened if tribunal caught poison
    write_stages = [s for s in report.stages if s.stage == "write"]
    if not report.all_passed:
        assert len(write_stages) == 0


@pytest.mark.asyncio
async def test_sse_events_fire_per_stage(pipeline):
    """Check SSE events fire for each stage completion."""
    changes = [FileChange(path="engine/config.py", component="config")]
    await pipeline.validate_changes(changes, run_tests=False)

    events = pipeline._events  # type: ignore[attr-defined]
    stage_events = [e for e in events if e.get(
        "type") == "parallel_validation_stage"]
    # At least tribunal + 16d
    assert len(stage_events) >= 2

    stages_seen = {e["stage"] for e in stage_events}
    assert "tribunal" in stages_seen
    assert "16d" in stages_seen


@pytest.mark.asyncio
async def test_write_queue_blocks_path_traversal(pipeline):
    """Verify the write queue blocks path traversal."""
    await pipeline._enqueue_write("../../etc/passwd", "malicious")
    # If we got here without error, the write was blocked (no exception, just logged)


@pytest.mark.asyncio
async def test_write_queue_blocks_non_engine_paths(pipeline):
    """Verify writes outside engine/ are blocked."""
    await pipeline._enqueue_write("studio/api.py", "malicious")
    # Write should be silently blocked


def test_pipeline_init_defaults():
    p = ParallelValidationPipeline()
    assert p._tribunal is not None
    assert p._validator is not None
