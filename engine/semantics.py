"""
engine/semantics.py — Unified semantic similarity and NLP utilities.

Provides consistent tokenization, stop-word filtering, and similarity metrics
(Jaccard, Cosine) across memory, cache, and vector store modules.
"""
import math
import re
from typing import Sequence

_STOP: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of",
    "is", "it", "its", "be", "are", "was", "were", "with", "this", "that",
    "as", "by", "from", "but", "not", "all", "each", "which", "both",
    "do", "does", "have", "has", "will", "can", "should", "must", "may",
    "we", "i", "you", "he", "she", "they", "their", "our", "your",
    "also", "use", "used", "using", "via", "per", "than", "more", "most",
})

def tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, filter stop words and short tokens."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP and len(t) > 1]

def jaccard_similarity(a: str | set[str] | list[str], b: str | set[str] | list[str]) -> float:
    """Jaccard similarity of token sets for two inputs (0.0 – 1.0)."""
    ta = set(tokenize(a)) if isinstance(a, str) else set(a)
    tb = set(tokenize(b)) if isinstance(b, str) else set(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def tf(tokens: list[str]) -> dict[str, float]:
    """Compute normalised term frequency."""
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    n = max(len(tokens), 1)
    return {t: c / n for t, c in freq.items()}

def cosine_sparse(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two sparse TF-IDF vectors."""
    if not a or not b:
        return 0.0
    dot = sum(a.get(t, 0.0) * v for t, v in b.items())
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (mag_a * mag_b) if mag_a > 0.0 and mag_b > 0.0 else 0.0

def cosine_dense(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity between two dense embedding vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0.0 and nb > 0.0 else 0.0
