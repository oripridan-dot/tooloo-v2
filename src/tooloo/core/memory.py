"""
3-Tier Sovereign Memory System
WHO: TooLoo Sovereign Hub
WHAT: Explicit, layered memory architecture for the MegaDAG and Buddy.
WHY: Rule 0 — no implicit or ghost state. Every memory tier is named, typed, and bounded.

Three tiers:
  TIER 1 — HOT   : In-process dict, instant R/W. Lives inside GlobalContext.state / Buddy prompt.
                   Scope: single DAG run. Lost on process exit.
  TIER 2 — WARM  : Session-scoped TTL store. Aggregates facts across multiple DAG ignitions
                   within the same process lifetime. Lost on process restart.
  TIER 3 — COLD  : File-backed KnowledgeBank (JSON). Persists across restarts.
                   Written only on reflection. Source of truth for learned heuristics.

Usage:
  # Attach one MemorySystem per entity (TooLoo DAG, Buddy)
  mem = MemorySystem(namespace="tooloo")
  mem.hot_write("last_goal", "Build the sovereign hub.")
  mem.warm_write("model_preference", "claude-3-7-sonnet", ttl_seconds=600)
  mem.cold_write("EACCES_FIX", "Always redirect /root writes to /tmp.")
  
  val = mem.read("last_goal")        # checks hot → warm → cold
"""

import time
import logging
from typing import Any, Dict, Optional
from src.tooloo.core.mega_dag import KnowledgeBank

logger = logging.getLogger("Tooloo.Memory")

class WarmStore:
    """
    Session-scoped TTL memory store (Tier 2).
    Holds key-value entries for at most `ttl_seconds` seconds.
    Lives in process memory; reset on restart.
    """

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}

    def write(self, key: str, value: Any, ttl_seconds: float = 300.0) -> None:
        self._data[key] = {"value": value, "expires_at": time.time() + ttl_seconds}
        logger.debug(f"[WARM] write '{key}' ttl={ttl_seconds}s")

    def read(self, key: str) -> Optional[Any]:
        entry = self._data.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._data[key]
            logger.debug(f"[WARM] '{key}' expired, evicted")
            return None
        return entry["value"]

    def evict_expired(self) -> int:
        before = len(self._data)
        now = time.time()
        self._data = {k: v for k, v in self._data.items() if v["expires_at"] > now}
        evicted = before - len(self._data)
        if evicted:
            logger.debug(f"[WARM] Evicted {evicted} expired entries")
        return evicted

    def snapshot(self) -> Dict[str, Any]:
        self.evict_expired()
        return {k: v["value"] for k, v in self._data.items()}


class MemorySystem:
    """
    Unified 3-tier memory facade for a named entity (e.g. 'tooloo' or 'buddy').

    Read order: Tier 1 (hot_store dict) → Tier 2 (warm TTL) → Tier 3 (KnowledgeBank).
    Write always goes to the specified tier only.
    """

    def __init__(self, namespace: str, hot_store: Optional[Dict[str, Any]] = None) -> None:
        self.namespace = namespace
        # Tier 1: caller-supplied mutable dict (e.g. GlobalContext.state) or private one
        self._hot: Dict[str, Any] = hot_store if hot_store is not None else {}
        # Tier 2: session TTL store
        self._warm = WarmStore()
        # Tier 3: file-backed KnowledgeBank
        self._cold = KnowledgeBank()
        logger.info(f"[MEMORY:{namespace}] Initialised. Cold lessons loaded: {len(self._cold.lessons)}")

    # ------------------------------------------------------------------ #
    # Write helpers                                                        #
    # ------------------------------------------------------------------ #

    def hot_write(self, key: str, value: Any) -> None:
        """Tier 1: instant, in-process. Survives only within this DAG run."""
        prefixed = f"{self.namespace}:{key}"
        self._hot[prefixed] = value
        logger.debug(f"[MEMORY:{self.namespace}] HOT write '{key}'")

    def warm_write(self, key: str, value: Any, ttl_seconds: float = 300.0) -> None:
        """Tier 2: session-scoped, expires after ttl_seconds."""
        prefixed = f"{self.namespace}:{key}"
        self._warm.write(prefixed, value, ttl_seconds)
        logger.debug(f"[MEMORY:{self.namespace}] WARM write '{key}' ttl={ttl_seconds}s")

    def cold_write(self, key: str, heuristic: str) -> None:
        """Tier 3: durable, file-backed KnowledgeBank lesson."""
        prefixed = f"{self.namespace}:{key}"
        self._cold.store_lesson(prefixed, heuristic)
        logger.debug(f"[MEMORY:{self.namespace}] COLD write '{key}'")

    # ------------------------------------------------------------------ #
    # Unified read — hot → warm → cold                                     #
    # ------------------------------------------------------------------ #

    def read(self, key: str) -> Optional[Any]:
        """
        Cascade read: Tier 1 first, then Tier 2, then Tier 3.
        Returns None if not found in any tier.
        """
        prefixed = f"{self.namespace}:{key}"

        # Tier 1
        if prefixed in self._hot:
            logger.debug(f"[MEMORY:{self.namespace}] HIT T1 '{key}'")
            return self._hot[prefixed]

        # Tier 2
        val = self._warm.read(prefixed)
        if val is not None:
            logger.debug(f"[MEMORY:{self.namespace}] HIT T2 '{key}'")
            return val

        # Tier 3
        lesson = self._cold.lessons.get(prefixed)
        if lesson is not None:
            logger.debug(f"[MEMORY:{self.namespace}] HIT T3 '{key}'")
            return lesson

        logger.debug(f"[MEMORY:{self.namespace}] MISS all tiers '{key}'")
        return None

    # ------------------------------------------------------------------ #
    # Diagnostics                                                          #
    # ------------------------------------------------------------------ #

    def diagnostics(self) -> Dict[str, Any]:
        self._warm.evict_expired()
        cold_ns = [k for k in self._cold.lessons if k.startswith(f"{self.namespace}:")]
        hot_ns = [k for k in self._hot if k.startswith(f"{self.namespace}:")]
        warm_ns = [k for k in self._warm.snapshot() if k.startswith(f"{self.namespace}:")]
        return {
            "namespace": self.namespace,
            "tier1_hot_keys": len(hot_ns),
            "tier2_warm_keys": len(warm_ns),
            "tier3_cold_keys": len(cold_ns),
            "cold_lessons_total": len(self._cold.lessons),
        }
