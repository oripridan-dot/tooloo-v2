# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: ASCENSION v2.1.0 — Sovereign Cognitive OS
# WHERE: engine.cognitive_dreamer.py
# WHEN: 2026-03-29T02:00:00.101010
# WHY: Final Repository Consolidation & Galactic Handover
# HOW: PURE Architecture Protocol
# ==========================================================

import asyncio
from dataclasses import dataclass
from typing import Any

from engine.vector_store import VectorStore
from engine.psyche_bank import PsycheBank
from engine.model_garden import ModelGarden
from engine.validator_16d import Validator16D


@dataclass
class DreamReport:
    fused_concepts: str
    insight_extracted: str
    garbage_purged_count: int
    consolidated_count: int = 0


_WHAT_IF_PROMPT_TEMPLATE = """You are in a cognitive dream state. Analyze the following two semantically close but unlinked system events/logs.
Narrow your focus by evaluating their relevance and VALUE against the following {dimension_count}D capability footprints: {dimensions}, and the user's overarching context.
What if they occurred simultaneously? Hallucinate edge cases, stress-test the system's limitations, and extract ONE actionable insight to improve the system.
If the logs have diminishing value but might be useful for long-term association, output <CONSOLIDATE> to compress them.
If the logs are verified as completely irrelevant garbage with zero associative value, output <PURGE>.
"""


class CognitiveDreamer:
    """Stateless dream engine for nocturnal optimization loops, with long-term memory consolidation."""

    def __init__(self, vector_store: Any, psyche_bank: Any, model_garden: Any):
        self._vector_store = vector_store
        self._psyche_bank = psyche_bank
        self._model_garden = model_garden

    async def run_dream_cycle(self) -> DreamReport:
        # Pull high-value context nodes for 16D/user context
        # (In complete implementation, queries contextual priority)
        results = self._vector_store.search("system events", top_k=2)
        if asyncio.iscoroutine(results):
            results = await results

        if len(results) < 2:
            return DreamReport("Insufficent logs", "None", 0, 0)

        c0 = getattr(results[0], "content", getattr(
            getattr(results[0], "doc", results[0]), "text", ""))
        c1 = getattr(results[1], "content", getattr(
            getattr(results[1], "doc", results[1]), "text", ""))
        id0 = results[0].id
        id1 = results[1].id

        fused_concepts = f"{c0} + {c1}"

        # Dynamically pull dimensions
        dims = Validator16D.get_dimension_names()
        dynamic_prompt = _WHAT_IF_PROMPT_TEMPLATE.format(
            dimension_count=len(dims),
            dimensions=", ".join(dims)
        )
        model_id = self._model_garden.get_tier_model(3, "DREAM")
        response = await self._model_garden.call(model_id=model_id, prompt=f"{dynamic_prompt}\n\n1: {c0}\n2: {c1}", intent="DREAM_16D_INTENTION_VECTOR")

        async def exec_sync_or_async(func, *args):
            res = func(*args)
            if asyncio.iscoroutine(res):
                return await res
            return res

        if "<PURGE>" in response:
            await exec_sync_or_async(self._vector_store.remove, id0)
            await exec_sync_or_async(self._vector_store.remove, id1)
            return DreamReport(fused_concepts, "Garbage Purged", 2, 0)

        elif "<CONSOLIDATE>" in response:
            compressed_content = f"Compressed memory: {c0[:20]}... + {c1[:20]}..."
            await exec_sync_or_async(self._vector_store.add, f"consolidated_{id0}_{id1}", compressed_content, {"status": "long_term_memory"})
            await exec_sync_or_async(self._vector_store.remove, id0)
            await exec_sync_or_async(self._vector_store.remove, id1)
            return DreamReport(fused_concepts, "Memories Consolidated", 0, 2)

        # Pass insight through Validator16D to ensure system quality
        validator = Validator16D()
        val_result = validator.validate(
            mandate_id="dream-cycle",
            intent="DREAM_INSIGHT",
            code_snippet=response,
            model_id_primary="gemini-2.5-flash"
        )

        if not val_result.autonomous_gate_pass:
            return DreamReport(fused_concepts, f"Rejected insight (16D Score: {val_result.composite_score:.2f})", 0, 0)

        # Capture as new generalized rule
        self._psyche_bank.capture("dream_insight", response)
        return DreamReport(fused_concepts, response, 0, 0)
