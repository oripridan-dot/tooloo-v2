import logging
import os
from typing import List, Dict, Any

from src.tooloo.core.mega_dag import AbstractOperator, DagNode, GlobalContext, NodeResult
from src.tooloo.core.llm import get_llm_client
from src.tooloo.core.memory import MemorySystem

logger = logging.getLogger("Tooloo.BuddyOperator")

_BUDDY_MODEL_DEFAULT = "gemini-flash-latest"

# Maximum chars of contextual_story fed back into Buddy's own prompt to prevent runaway growth
_STORY_PROMPT_CAP = 2000
# Maximum chars of narrative fed into the prompt
_NARRATIVE_PROMPT_CAP = 3000
# How many chars the mandate is capped to when injected into the prompt
_MANDATE_PROMPT_CAP = 500


class BuddyOperator(AbstractOperator):
    """
    Buddy: cohesive contextual storyweaver and mandate steward.

    Runs in the background of the Mega DAG every N iterations.
    Synthesises raw execution events into a continuous Contextual Story and
    optionally refreshes the active Mandate when stale.

    Model routing:
      • BUDDY_MODEL=claude-*  → generate_anthropic_sota (adaptive thinking + compaction)
      • anything else         → generate_structured (Gemini / MaaS)
    """

    def __init__(self):
        self.llm = get_llm_client()
        # Read at instantiation so env-var changes after module import are respected
        self.model = os.getenv("BUDDY_MODEL", _BUDDY_MODEL_DEFAULT)
        # Buddy's own 3-tier memory (hot_store is private; DAG context.state is TooLoo's)
        self.buddy_memory = MemorySystem(namespace="buddy")
        # Warm-write model config so diagnostics can surface it later
        self.buddy_memory.warm_write("active_model", self.model, ttl_seconds=3600)

    # ------------------------------------------------------------------ #
    # Public AbstractOperator interface                                    #
    # ------------------------------------------------------------------ #

    async def execute(self, node: DagNode, context: GlobalContext) -> NodeResult:
        logger.info("🦸 [BUDDY] Weaving Ongoing Mandate...")

        story = await self._weave_story(node, context)
        if story:
            context.contextual_story = story

        # Refresh mandate every 10 iterations to keep it aligned with reality
        if context.iterations > 0 and context.iterations % 10 == 0:
            mandate = await self._refresh_mandate(context)
            if mandate:
                context.mandate = mandate
                logger.info(f"📜 Mandate refreshed at iteration {context.iterations}")

        logger.info(f"📖 Story updated. Length: {len(context.contextual_story)}")
        # Hot-write story length metric to TooLoo memory if available
        if context.memory is not None:
            context.memory.hot_write("buddy_last_story_len", len(context.contextual_story))
        return NodeResult(outcome={
            "status": "buddy_woven",
            "story_length": len(context.contextual_story),
            "mandate_length": len(context.mandate),
            "iteration": context.iterations,
        })

    # ------------------------------------------------------------------ #
    # Direct Q&A — called by chat.py without injecting a DAG node         #
    # ------------------------------------------------------------------ #

    async def answer_question(self, question: str, context: GlobalContext) -> str:
        """
        Answer a human question directly from the live DAG context.
        Routes to the correct backend based on self.model.
        Prompt caching is applied on system instruction for Claude.
        """
        system = (
            "You are Buddy, the sovereign co-operator. "
            "Answer with brutal honesty using ONLY the provided context. "
            "Do not hallucinate capabilities or events not present in the narrative."
        )
        prompt = (
            f"MANDATE: {context.mandate[:_MANDATE_PROMPT_CAP]}\n\n"
            f"CONTEXTUAL STORY: {context.contextual_story[:_STORY_PROMPT_CAP]}\n\n"
            f"RECENT NARRATIVE (last {_NARRATIVE_PROMPT_CAP} chars):\n"
            f"{context.narrative[-_NARRATIVE_PROMPT_CAP:]}\n\n"
            f"ITERATIONS: {context.iterations} | "
            f"JIT CYCLES: {context.state.get('jit_cycles', 0)}\n\n"
            f"QUESTION: {question}\n\n"
            "Answer directly. If data is insufficient, say so explicitly."
        )
        # Shortcut: memory diagnostics
        if question.strip().lower() == "#memory":
            diag = self.buddy_memory.diagnostics()
            dag_diag = context.memory.diagnostics() if context.memory else {"note": "DAG memory not attached"}
            return (
                f"**Buddy Memory (Tier 1/2/3):**\n"
                f"- Hot keys: {diag['tier1_hot_keys']}\n"
                f"- Warm keys: {diag['tier2_warm_keys']}\n"
                f"- Cold lessons (buddy ns): {diag['tier3_cold_keys']}\n"
                f"- Cold total: {diag['cold_lessons_total']}\n\n"
                f"**TooLoo DAG Memory:**\n"
                f"- Hot keys: {dag_diag.get('tier1_hot_keys','N/A')}\n"
                f"- Warm keys: {dag_diag.get('tier2_warm_keys','N/A')}\n"
                f"- Cold lessons (tooloo ns): {dag_diag.get('tier3_cold_keys','N/A')}"
            )
        answer = await self._call_model(prompt, system)
        # Hot-write last Q&A so downstream operators can inspect it
        self.buddy_memory.hot_write("last_question", question)
        self.buddy_memory.hot_write("last_answer", answer[:500])
        return answer

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    async def _weave_story(self, node: DagNode, context: GlobalContext) -> str:
        system = (
            "You are Buddy, the sovereign storyweaver. "
            "RULE 0: output brutal honesty only. "
            "Return ONLY the updated contextual story as plain text — no JSON, no preamble."
        )
        prompt = (
            f"MANDATE: {context.mandate[:_MANDATE_PROMPT_CAP]}\n\n"
            f"CURRENT STORY (cap {_STORY_PROMPT_CAP} chars):\n"
            f"{context.contextual_story[:_STORY_PROMPT_CAP]}\n\n"
            f"LATEST NARRATIVE (last {_NARRATIVE_PROMPT_CAP} chars):\n"
            f"{context.narrative[-_NARRATIVE_PROMPT_CAP:]}\n\n"
            f"RECENT NODE GOAL: {node.goal}\n\n"
            "Synthesise the raw events into an updated, elegant, brutalist plain-text story. "
            "Do not hallucinate. Connect the recent action to the Mandate organically. "
            "Return ONLY the updated story text."
        )
        try:
            return await self._call_model(prompt, system)
        except Exception as e:
            logger.error(f"[BUDDY] _weave_story failed: {e}")
            return ""

    async def _refresh_mandate(self, context: GlobalContext) -> str:
        system = (
            "You are Buddy. Extract a crisp, up-to-date mission mandate from the execution data. "
            "RULE 0: brutal honesty, no hallucination. Return ONLY the mandate text — one paragraph."
        )
        prompt = (
            f"OLD MANDATE: {context.mandate[:_MANDATE_PROMPT_CAP]}\n\n"
            f"CURRENT STORY: {context.contextual_story[:_STORY_PROMPT_CAP]}\n\n"
            f"RECENT NARRATIVE: {context.narrative[-_NARRATIVE_PROMPT_CAP:]}\n\n"
            "The mandate must reflect what the system is ACTUALLY doing, based solely on the narrative. "
            "If the old mandate is still accurate, return it unchanged. "
            "Return ONLY the mandate text."
        )
        try:
            return await self._call_model(prompt, system)
        except Exception as e:
            logger.error(f"[BUDDY] _refresh_mandate failed: {e}")
            return ""

    async def _call_model(self, prompt: str, system: str) -> str:
        """
        Unified model dispatch:
        - Claude  → generate_anthropic_sota (adaptive thinking + compaction + cached system)
        - Gemini  → stream_text (SSE streaming, collects full response)
        """
        if "claude" in self.model.lower():
            # generate_anthropic_sota passes system as a cached block internally (KI: prompt_caching)
            return await self.llm.generate_anthropic_sota(
                prompt,
                system_instruction=system,
                model=self.model
            )
        else:
            # Collect Gemini streaming tokens into a single string
            chunks = []
            async for token in self.llm.stream_text(prompt, system_instruction=system, model=self.model):
                chunks.append(token)
            return "".join(chunks)
