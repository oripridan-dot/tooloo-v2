"""tests/test_semantics.py — Coverage for engine/semantics.py.

Tests:
  - tokenize: lowercasing, stop-word removal, short-token filtering, punctuation
  - jaccard_similarity: identical strings, disjoint, partial overlap, empty inputs
  - tf: frequency computation and normalisation
  - cosine_sparse: orthogonal, identical, partial overlap, empty dicts
  - cosine_dense: identical, orthogonal, partial overlap, mismatched lengths
"""
from __future__ import annotations

import math

import pytest

from engine.semantics import (
    cosine_dense,
    cosine_sparse,
    jaccard_similarity,
    tf,
    tokenize,
)


class TestTokenize:
    """Tests for the tokenize helper."""

    def test_lowercases_input(self) -> None:
        tokens = tokenize("Hello World")
        assert "hello" in tokens
        assert "world" in tokens

    def test_strips_punctuation(self) -> None:
        tokens = tokenize("what's up? it's cool!")
        assert "cool" in tokens
        # stop words removed
        assert "its" not in tokens

    def test_removes_stop_words(self) -> None:
        tokens = tokenize("the and or in on at to for")
        assert tokens == []

    def test_removes_short_tokens(self) -> None:
        tokens = tokenize("a b c do it by")
        # single-char ('a', 'b', 'c') should be removed
        assert "a" not in tokens

    def test_preserves_long_meaningful_tokens(self) -> None:
        tokens = tokenize("neural architecture search")
        assert "neural" in tokens
        assert "architecture" in tokens
        assert "search" in tokens

    def test_handles_empty_string(self) -> None:
        assert tokenize("") == []

    def test_numbers_as_tokens(self) -> None:
        tokens = tokenize("api version 2025")
        assert "version" in tokens
        assert "2025" in tokens

    def test_deduplication_not_done(self) -> None:
        # tokenize returns all occurrences (caller deduplicates if needed)
        tokens = tokenize("build build build")
        assert tokens.count("build") == 3


class TestJaccardSimilarity:
    """Tests for jaccard_similarity."""

    def test_identical_strings_return_one(self) -> None:
        assert jaccard_similarity(
            "fast api python", "fast api python") == pytest.approx(1.0)

    def test_disjoint_strings_return_zero(self) -> None:
        assert jaccard_similarity(
            "apple orange", "rocket science") == pytest.approx(0.0)

    def test_partial_overlap(self) -> None:
        score = jaccard_similarity("fast api python", "fast neural network")
        assert 0 < score < 1

    def test_empty_string_vs_empty_string(self) -> None:
        # Both empty → similarity 1.0 (trivially identical)
        assert jaccard_similarity("", "") == pytest.approx(1.0)

    def test_empty_vs_nonempty(self) -> None:
        assert jaccard_similarity("", "python") == pytest.approx(0.0)

    def test_accepts_sets(self) -> None:
        # Should work when called with pre-tokenized sets
        a = {"fast", "api"}
        b = {"fast", "network"}
        score = jaccard_similarity(a, b)
        # intersection={fast}, union={fast,api,network} → 1/3
        assert score == pytest.approx(1 / 3)

    def test_symmetric(self) -> None:
        a = "machine learning pipeline"
        b = "deep learning model"
        assert jaccard_similarity(a, b) == pytest.approx(
            jaccard_similarity(b, a))


class TestTf:
    """Tests for tf (term frequency)."""

    def test_single_token(self) -> None:
        result = tf(["python"])
        assert result == {"python": pytest.approx(1.0)}

    def test_equal_tokens(self) -> None:
        result = tf(["a", "a", "b", "b"])
        assert result["a"] == pytest.approx(0.5)
        assert result["b"] == pytest.approx(0.5)

    def test_empty_returns_empty(self) -> None:
        # max(0, 1) prevents ZeroDivisionError
        result = tf([])
        assert result == {}

    def test_frequency_normalised(self) -> None:
        tokens = ["x", "x", "x", "y"]
        result = tf(tokens)
        # x: 3/4, y: 1/4
        assert result["x"] == pytest.approx(0.75)
        assert result["y"] == pytest.approx(0.25)

    def test_sum_of_frequencies_is_one(self) -> None:
        tokens = ["a", "b", "c", "a", "b", "a"]
        result = tf(tokens)
        assert sum(result.values()) == pytest.approx(1.0)


class TestCosineSparse:
    """Tests for cosine_sparse (sparse TF-IDF vectors)."""

    def test_identical_vectors_return_one(self) -> None:
        v = {"python": 0.5, "api": 0.5}
        assert cosine_sparse(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self) -> None:
        a = {"python": 1.0}
        b = {"java": 1.0}
        assert cosine_sparse(a, b) == pytest.approx(0.0)

    def test_partial_overlap(self) -> None:
        a = {"python": 0.8, "api": 0.6}
        b = {"python": 0.8, "ml": 0.6}
        score = cosine_sparse(a, b)
        assert 0 < score < 1

    def test_empty_vectors_return_zero(self) -> None:
        assert cosine_sparse({}, {}) == pytest.approx(0.0)
        assert cosine_sparse({"a": 1.0}, {}) == pytest.approx(0.0)

    def test_symmetric(self) -> None:
        a = {"x": 0.6, "y": 0.4}
        b = {"x": 0.3, "z": 0.7}
        assert cosine_sparse(a, b) == pytest.approx(cosine_sparse(b, a))


class TestCosineDense:
    """Tests for cosine_dense (dense embedding vectors)."""

    def test_identical_vectors_return_one(self) -> None:
        v = [0.5, 0.5, 0.5, 0.5]
        assert cosine_dense(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_dense(a, b) == pytest.approx(0.0)

    def test_partial_overlap(self) -> None:
        a = [1.0, 0.5]
        b = [0.5, 1.0]
        score = cosine_dense(a, b)
        assert 0 < score < 1

    def test_empty_sequences_return_zero(self) -> None:
        assert cosine_dense([], []) == pytest.approx(0.0)

    def test_mismatched_lengths_return_zero(self) -> None:
        assert cosine_dense([1.0, 2.0], [1.0, 2.0, 3.0]) == pytest.approx(0.0)

    def test_zero_vector_returns_zero(self) -> None:
        assert cosine_dense([0.0, 0.0], [1.0, 2.0]) == pytest.approx(0.0)

    def test_symmetric(self) -> None:
        a = [0.3, 0.7, 0.1]
        b = [0.9, 0.1, 0.4]
        assert cosine_dense(a, b) == pytest.approx(cosine_dense(b, a))

    def test_known_value(self) -> None:
        a = [1.0, 0.0]
        b = [1.0, 1.0]
        # cos(45°) = sqrt(2)/2 ≈ 0.7071
        expected = 1.0 / math.sqrt(2)
        assert cosine_dense(a, b) == pytest.approx(expected, rel=1e-4)
