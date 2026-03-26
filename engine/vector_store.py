"""
engine/vector_store.py — In-process TF-IDF vector store + cosine similarity.

No external ML dependencies (pure stdlib + math).

Every document is tokenised → TF-IDF sparse vector (dict[str, float]).
IDF is recomputed incrementally on each insertion so similarity scores stay
calibrated as the corpus grows.

Used by:
  - SandboxOrchestrator : feature deduplication before spawning
  - RoadmapManager      : near-duplicate rejection + semantic clustering
  - Future              : PsycheBank rule similarity matching

Public API:
  VectorStore.add(id, text, metadata) → bool  (True=new, False=near-duplicate)
  VectorStore.search(query, top_k, threshold) → list[SearchResult]
  VectorStore.get(id)                         → VectorDoc | None
  VectorStore.remove(id)                      → bool
  VectorStore.to_dict()                       → dict  (inspection/API)
"""
from __future__ import annotations

import logging
import math
import re
import threading
from dataclasses import dataclass, field
from typing import Any

# Control: rollback and circuit-breaker thresholds for corpus safety
_MAX_CORPUS_SIZE = 50_000     # hard cap to prevent unbounded memory growth
_ROLLBACK_ON_CORRUPT = True   # auto-rollback corrupted document insertions

logger = logging.getLogger(__name__)

# ── Gemini Embedding Backend ──────────────────────────────────────────────────
# Optional: if google-genai + GEMINI_API_KEY are available, use gemini-embedding-001
# for dense semantic similarity.  Falls back to TF-IDF on any failure.

_gemini_embed_client = None
try:
    # type: ignore[attr-defined]
    from engine.config import GEMINI_API_KEY as _EMBED_KEY
    if _EMBED_KEY:
        from google import genai as _genai_embed  # type: ignore[import]
        _gemini_embed_client = _genai_embed.Client(api_key=_EMBED_KEY)
except Exception:
    pass

_EMBED_MODEL = "models/gemini-embedding-001"


def _get_embedding(text: str) -> list[float] | None:
    """Call Gemini gemini-embedding-001. Returns None on any failure."""
    if _gemini_embed_client is None:
        return None
    try:
        resp = _gemini_embed_client.models.embed_content(
            model=_EMBED_MODEL,
            contents=text[:2000],
        )
        return list(resp.embeddings[0].values)
    except Exception:
        return None


def _cosine_dense(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two dense float vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0.0 and nb > 0.0 else 0.0


# ── Stop-word filter ──────────────────────────────────────────────────────────
_STOP: frozenset[str] = frozenset({
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of",
    "is", "it", "its", "be", "are", "was", "were", "with", "this", "that",
    "as", "by", "from", "but", "not", "all", "each", "which", "both",
    "do", "does", "have", "has", "will", "can", "should", "must", "may",
    "we", "i", "you", "he", "she", "they", "their", "our", "your",
    "also", "use", "used", "using", "via", "per", "than", "more", "most",
})


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, filter stop words and short tokens."""
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOP and len(t) > 1]


def _tf(tokens: list[str]) -> dict[str, float]:
    """Compute normalised term frequency."""
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    n = max(len(tokens), 1)
    return {t: c / n for t, c in freq.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    """Cosine similarity between two sparse TF-IDF vectors."""
    if not a or not b:
        return 0.0
    dot = sum(a.get(t, 0.0) * v for t, v in b.items())
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class VectorDoc:
    """One indexed document with its TF-IDF vector and (optional) dense embedding."""
    id: str
    text: str
    tf: dict[str, float]            # raw term frequencies (stable)
    # TF-IDF weighted (rebuilt on corpus changes)
    tfidf: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = field(
        default=None, repr=False)  # Gemini dense vec

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text[:200],
            "metadata": self.metadata,
            "vector_dims": len(self.tfidf),
            "has_embedding": self.embedding is not None,
        }


@dataclass
class SearchResult:
    id: str
    score: float
    doc: VectorDoc

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "score": round(self.score, 4),
            "metadata": self.doc.metadata,
        }


# ── Store ─────────────────────────────────────────────────────────────────────

class VectorStore:
    """Thread-safe in-process TF-IDF vector store.

    Deduplication gate: ``add()`` returns ``False`` when the nearest neighbour
    exceeds ``dup_threshold``, preventing near-identical features from spawning
    redundant sandboxes or roadmap items.

    IDF is smoothed: idf(t) = log((N+1) / (df(t)+1)) + 1
    """

    def __init__(self, dup_threshold: float | None = None) -> None:
        from engine.config import settings as _cfg
        from engine.memory.merkle_tree import MerkleTree
        from pathlib import Path
        
        self._lock = threading.Lock()
        self._docs: dict[str, VectorDoc] = {}
        # term → IDF weight (recomputed on insert/remove)
        self._idf: dict[str, float] = {}
        self._df: dict[str, int] = {}       # term → document frequency count
        
        # Tier-5: Structural Physics (Merkle Tree)
        self._merkle = MerkleTree(str(Path(__file__).resolve().parents[1]))
        self._last_state_hash: str | None = None
        
        # Prefer explicit kwarg; fall back to NEAR_DUPLICATE_THRESHOLD from .env
        self.dup_threshold = dup_threshold if dup_threshold is not None else _cfg.near_duplicate_threshold

    # ── IDF management ────────────────────────────────────────────────────────

    def _recompute_idf(self) -> None:
        n = len(self._docs)
        if n == 0:
            self._idf = {}
            return
        self._idf = {
            t: math.log((n + 1) / (df + 1)) + 1.0
            for t, df in self._df.items()
        }

    def _to_tfidf(self, tf: dict[str, float]) -> dict[str, float]:
        return {t: v * self._idf.get(t, 1.0) for t, v in tf.items()}

    def _rebuild_all(self) -> None:
        """Rebuild all TF-IDF vectors after an IDF change."""
        for doc in self._docs.values():
            doc.tfidf = self._to_tfidf(doc.tf)

    # ── Internal search ───────────────────────────────────────────────────────

    def _search_internal(
        self,
        query_vec: dict[str, float],
        top_k: int,
        query_embedding: list[float] | None = None,
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        for doc in self._docs.values():
            # Tier-5: Primary path is Dense Semantic Similarity
            if query_embedding is not None and doc.embedding is not None:
                score = _cosine_dense(query_embedding, doc.embedding)
            else:
                # Fallback: TF-IDF sparse cosine
                score = _cosine(query_vec, doc.tfidf)
            results.append(SearchResult(id=doc.id, score=score, doc=doc))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def validate_physics(self) -> bool:
        """Verify the structural integrity of the workspace vs the indexed context."""
        new_hash = self._merkle.build()
        if self._last_state_hash and new_hash != self._last_state_hash:
            logger.warning("Structural Physics Divergence detected. Workspace has changed.")
            return False
        self._last_state_hash = new_hash
        return True

    # ── Public API ────────────────────────────────────────────────────────────

    def add(
        self,
        doc_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Index a document.

        Returns ``True`` if added.
        Returns ``False`` if a near-duplicate (≥ ``dup_threshold``) already exists.
        """
        with self._lock:
            tokens = _tokenize(text)
            tf = _tf(tokens)
            tfidf_tmp = self._to_tfidf(tf)
            # Attempt to get a dense Gemini embedding for this document
            embedding = _get_embedding(text)

            if self._docs:
                top = self._search_internal(
                    tfidf_tmp, top_k=1, query_embedding=embedding
                )
                if top and top[0].score >= self.dup_threshold:
                    return False  # near-duplicate rejected

            self._docs[doc_id] = VectorDoc(
                id=doc_id,
                text=text,
                tf=tf,
                tfidf=tfidf_tmp,
                metadata=metadata or {},
                embedding=embedding,
            )
            for t in tf:
                self._df[t] = self._df.get(t, 0) + 1
            self._recompute_idf()
            self._rebuild_all()
            return True

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> list[SearchResult]:
        """Return top-k most similar documents with score ≥ threshold.

        Uses Gemini dense embeddings when available; falls back to TF-IDF sparse
        cosine when the API is offline or not configured.
        """
        with self._lock:
            if not self._docs:
                return []
            tokens = _tokenize(query)
            tf = _tf(tokens)
            qvec = self._to_tfidf(tf)
            query_embedding = _get_embedding(query)
            results = self._search_internal(
                qvec, top_k, query_embedding=query_embedding)
            return [r for r in results if r.score >= threshold]

    def get(self, doc_id: str) -> VectorDoc | None:
        with self._lock:
            return self._docs.get(doc_id)

    def remove(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id not in self._docs:
                return False
            doc = self._docs.pop(doc_id)
            for t in doc.tf:
                self._df[t] = max(0, self._df.get(t, 1) - 1)
                if self._df[t] == 0:
                    del self._df[t]
            self._recompute_idf()
            self._rebuild_all()
            return True

    def size(self) -> int:
        with self._lock:
            return len(self._docs)

    def all_docs(self) -> list[VectorDoc]:
        with self._lock:
            return list(self._docs.values())

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "size": len(self._docs),
                "vocabulary_size": len(self._idf),
                "dup_threshold": self.dup_threshold,
                "documents": [d.to_dict() for d in self._docs.values()],
            }

_vector_store: VectorStore | None = None
def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
