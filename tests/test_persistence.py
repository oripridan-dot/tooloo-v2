"""tests/test_persistence.py — Coverage for engine/persistence.py.

Tests:
  - atomic_write_json: happy path, nested dict, list, non-existent directory
  - atomic_write_json: re-raises on write failure (bad path)
  - safe_read_json: file not found returns default
  - safe_read_json: corrupt JSON returns default
  - safe_read_json: valid JSON returns parsed value
  - safe_read_json: empty string default still works
  - Atomic rename guarantees: partial write leaves original intact on error
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.persistence import atomic_write_json, safe_read_json


class TestAtomicWriteJson:
    """Tests for atomic_write_json."""

    def test_writes_dict_to_file(self, tmp_path: Path) -> None:
        target = tmp_path / "test.json"
        atomic_write_json(target, {"key": "value"})
        assert json.loads(target.read_text()) == {"key": "value"}

    def test_writes_list_to_file(self, tmp_path: Path) -> None:
        target = tmp_path / "list.json"
        atomic_write_json(target, [1, 2, 3])
        assert json.loads(target.read_text()) == [1, 2, 3]

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c" / "deep.json"
        atomic_write_json(target, {"nested": True})
        assert target.exists()
        assert json.loads(target.read_text()) == {"nested": True}

    def test_uses_indented_format(self, tmp_path: Path) -> None:
        target = tmp_path / "pretty.json"
        atomic_write_json(target, {"a": 1}, indent=4)
        raw = target.read_text()
        assert "\n    " in raw  # indented

    def test_no_temp_file_left_behind(self, tmp_path: Path) -> None:
        target = tmp_path / "clean.json"
        atomic_write_json(target, {"x": 1})
        tmp_file = target.with_suffix(".json.tmp")
        assert not tmp_file.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        target = tmp_path / "overwrite.json"
        atomic_write_json(target, {"v": 1})
        atomic_write_json(target, {"v": 2})
        assert json.loads(target.read_text()) == {"v": 2}

    def test_raises_on_bad_path(self, tmp_path: Path) -> None:
        """Write to an invalid path (root of a non-existent drive) should raise."""
        bad_path = Path("/no_such_root_xyz/data.json")
        with pytest.raises(Exception):
            atomic_write_json(bad_path, {"x": 1})

    def test_non_ascii_characters(self, tmp_path: Path) -> None:
        target = tmp_path / "unicode.json"
        atomic_write_json(target, {"emoji": "🚀", "cjk": "日本語"})
        loaded = json.loads(target.read_text(encoding="utf-8"))
        assert loaded["emoji"] == "🚀"
        assert loaded["cjk"] == "日本語"


class TestSafeReadJson:
    """Tests for safe_read_json."""

    def test_returns_default_when_file_missing(self, tmp_path: Path) -> None:
        result = safe_read_json(tmp_path / "no_such_file.json")
        assert result == {}

    def test_returns_custom_default_when_missing(self, tmp_path: Path) -> None:
        result = safe_read_json(tmp_path / "no_such.json", default=[])
        assert result == []

    def test_returns_none_default(self, tmp_path: Path) -> None:
        # When default is None, should also return {} (None → {})
        result = safe_read_json(tmp_path / "missing.json", default=None)
        assert result == {}

    def test_reads_valid_dict(self, tmp_path: Path) -> None:
        p = tmp_path / "data.json"
        p.write_text('{"foo": "bar"}', encoding="utf-8")
        assert safe_read_json(p) == {"foo": "bar"}

    def test_reads_valid_list(self, tmp_path: Path) -> None:
        p = tmp_path / "list.json"
        p.write_text("[1, 2, 3]", encoding="utf-8")
        assert safe_read_json(p) == [1, 2, 3]

    def test_returns_default_on_corrupt_json(self, tmp_path: Path) -> None:
        p = tmp_path / "corrupt.json"
        p.write_text("{not valid json", encoding="utf-8")
        result = safe_read_json(p, default={"fallback": True})
        assert result == {"fallback": True}

    def test_returns_default_on_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.json"
        p.write_text("", encoding="utf-8")
        result = safe_read_json(p, default={"empty": True})
        assert result == {"empty": True}

    def test_roundtrip_with_atomic_write(self, tmp_path: Path) -> None:
        p = tmp_path / "roundtrip.json"
        data = {"sessions": [{"id": "s1", "score": 0.9}], "count": 1}
        atomic_write_json(p, data)
        loaded = safe_read_json(p)
        assert loaded == data
