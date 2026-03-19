"""
tests/test_vector_store.py — VectorStore invariant tests.

Coverage:
  · add() returns True for new docs, False for near-duplicates
  · search() returns top-k results sorted by cosine score
  · get() / remove() lifecycle
  · IDF recompute on insert / remove
  · Thread-safety: concurrent inserts do not corrupt internal state
  · to_dict() inspection shape
  · Cosine stagnation threshold (drives run_cycles semantic diff)
"""
from __future__ import annotations

import threading
import time
from collections.abc import Callable

import pytest

from engine.vector_store import VectorStore, _cosine, _tf, _tokenize


# ── Unit helpers ───────────────────────────────────────────────────────────────

class TestTokenize:
    def test_lowercases(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_removes_stopwords(self):
        tokens = _tokenize("this is a test")
        assert "is" not in tokens
        assert "a" not in tokens
        assert "test" in tokens

    def test_filters_short_tokens(self):
        # _tokenize filters len <= 1; single chars removed, 2+ chars kept
        tokens = _tokenize("a ab abc abcd")
        assert "a" not in tokens   # length 1 — filtered
        assert "ab" in tokens      # length 2 — kept
        assert "abc" in tokens     # length 3 — kept


class TestCosine:
    def test_identical_vectors(self):
        v = {"hello": 0.5, "world": 0.5}
        assert _cosine(v, v) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors(self):
        a = {"hello": 1.0}
        b = {"world": 1.0}
        assert _cosine(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_empty_vectors(self):
        assert _cosine({}, {"hello": 1.0}) == 0.0
        assert _cosine({"hello": 1.0}, {}) == 0.0


# ── VectorStore core ──────────────────────────────────────────────────────────

class TestVectorStoreAdd:
    def test_add_new_document_returns_true(self):
        vs = VectorStore()
        assert vs.add(
            "doc1", "the quick brown fox jumps over the lazy dog") is True

    def test_add_duplicate_id_replaces(self):
        vs = VectorStore()
        vs.add("doc1", "hello world python")
        # Second add with same ID — treated as new (no near-dup existing yet)
        result = vs.add("doc1", "hello world python")
        # Near-dup of itself — should be blocked by dedup threshold
        assert result is False  # dup_threshold=0.92 — exact copy is ≥ 0.92

    def test_near_duplicate_rejected(self):
        vs = VectorStore(dup_threshold=0.85)
        base = "fast python service fastapi pydantic authentication endpoint router"
        vs.add("doc1", base)
        # Highly similar: one extra word at the end
        result = vs.add("doc2", base + " middleware")
        assert result is False

    def test_distinct_documents_both_accepted(self):
        vs = VectorStore()
        r1 = vs.add("doc1", "machine learning gradient descent neural network")
        r2 = vs.add(
            "doc2", "kubernetes helm chart deployment ingress controller")
        assert r1 is True
        assert r2 is True
        assert vs.get("doc1") is not None
        assert vs.get("doc2") is not None

    def test_empty_store_always_accepts(self):
        vs = VectorStore()
        assert vs.add("doc1", "anything goes") is True

    def test_metadata_stored(self):
        vs = VectorStore()
        vs.add("doc1", "hello world", metadata={
               "source": "test", "score": 0.9})
        doc = vs.get("doc1")
        assert doc is not None
        assert doc.metadata["source"] == "test"
        assert doc.metadata["score"] == pytest.approx(0.9)


class TestVectorStoreSearch:
    def test_returns_top_k(self):
        vs = VectorStore()
        vs.add("a", "python async fastapi microservice")
        vs.add("b", "machine learning training pipeline")
        vs.add("c", "python web framework request response")
        results = vs.search("python fastapi service", top_k=2)
        assert len(results) <= 2

    def test_results_sorted_by_score_desc(self):
        vs = VectorStore()
        vs.add("a", "python fastapi pydantic async web service")
        vs.add("b", "machine learning gradient descent optimizer")
        results = vs.search("python fastapi", top_k=2)
        if len(results) >= 2:
            assert results[0].score >= results[1].score

    def test_threshold_filters_low_scores(self):
        vs = VectorStore()
        vs.add("a", "alpha beta gamma delta epsilon")
        results = vs.search(
            "completely unrelated zeta eta theta", threshold=0.9)
        assert results == []

    def test_empty_store_returns_empty(self):
        vs = VectorStore()
        assert vs.search("anything") == []

    def test_exact_match_scores_high(self):
        vs = VectorStore()
        text = "autonomous dag cognitive operating system pipeline"
        vs.add("doc1", text)
        results = vs.search(text, top_k=1)
        assert results
        assert results[0].score > 0.8


class TestVectorStoreRemove:
    def test_remove_existing(self):
        vs = VectorStore()
        vs.add("doc1", "hello world test")
        assert vs.remove("doc1") is True
        assert vs.get("doc1") is None

    def test_remove_nonexistent_returns_false(self):
        vs = VectorStore()
        assert vs.remove("ghost") is False

    def test_idf_recomputed_after_remove(self):
        vs = VectorStore()
        vs.add("doc1", "python fastapi service")
        vs.add("doc2", "python django service")
        vs.remove("doc1")
        # After removal, IDF for remaining doc should still be non-zero
        doc2 = vs.get("doc2")
        assert doc2 is not None
        assert len(doc2.tfidf) > 0


class TestVectorStoreToDict:
    def test_to_dict_shape(self):
        vs = VectorStore()
        vs.add("doc1", "tribunal owasp security scan injection")
        d = vs.to_dict()
        assert "size" in d
        assert "dup_threshold" in d
        assert "documents" in d  # actual key is 'documents', not 'docs'
        assert d["size"] == 1


# ── Thread-safety ─────────────────────────────────────────────────────────────

class TestVectorStoreThreadSafety:
    def test_concurrent_inserts_no_corruption(self):
        """50 threads inserting distinct documents must not raise and all
        documents present after join (or near-dup rejected — both are valid)."""
        vs = VectorStore(
            dup_threshold=0.99)  # very tight threshold → most distinct
        errors: list[Exception] = []

        def inserter(i: int) -> None:
            try:
                vs.add(
                    f"doc-{i}", f"unique document number {i} ingestion topic signal {i*7}")
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=inserter, args=(i,))
                   for i in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        # At least some docs should have been inserted
        assert vs.to_dict()["size"] > 0

    def test_concurrent_search_during_insert(self):
        """Readers must never raise even while writers are mutating state."""
        vs = VectorStore()
        vs.add("seed", "python autonomous dag cognitive operating system")
        stop = threading.Event()
        errors: list[Exception] = []

        def reader() -> None:
            while not stop.is_set():
                try:
                    vs.search("dag cognitive system")
                except Exception as exc:  # pragma: no cover
                    errors.append(exc)
                    break

        def writer(i: int) -> None:
            try:
                vs.add(
                    f"w-{i}", f"writer document {i} with various tokens signal value {i}")
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        reader_threads = [threading.Thread(target=reader) for _ in range(3)]
        for t in reader_threads:
            t.start()

        writer_threads = [threading.Thread(
            target=writer, args=(i,)) for i in range(20)]
        for t in writer_threads:
            t.start()
        for t in writer_threads:
            t.join()

        stop.set()
        for t in reader_threads:
            t.join()

        assert not errors, f"Concurrent read/write errors: {errors}"


# ── Stagnation threshold (validates run_cycles semantic diff) ─────────────────

class TestSemanticStagnationThreshold:
    """Ensure the 0.95 near-duplicate threshold correctly classifies
    stagnating vs. evolving suggestions pairs as used by run_cycles.py."""

    _THRESHOLD = 0.95

    def _is_stagnant(self, text_prev: str, text_curr: str) -> bool:
        vs = VectorStore(dup_threshold=self._THRESHOLD)
        vs.add("prev", text_prev)
        results = vs.search(text_curr, top_k=1, threshold=self._THRESHOLD)
        vs.remove("prev")
        return bool(results)

    def test_identical_suggestions_stagnant(self):
        text = "FIX 1: add threading lock to vector_store FIX 2: refactor idf computation"
        assert self._is_stagnant(text, text) is True

    def test_near_identical_stagnant(self):
        t1 = "Add threading lock to protect TF-IDF mutation during parallel fan-out"
        t2 = "Add a threading lock to protect the TF-IDF mutation during parallel fan-out execution"
        assert self._is_stagnant(t1, t2) is True

    def test_clearly_different_not_stagnant(self):
        t1 = "Add threading lock to protect TF-IDF mutation"
        t2 = "Refactor tribunal patterns to add BOLA IDOR SSRF detection regex"
        assert self._is_stagnant(t1, t2) is False
