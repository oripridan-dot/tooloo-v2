"""
engine/meta_architect.py — Dynamic DAG synthesis for AI-native execution.

Meta-Architect responsibilities:
  1. Assess whether deeper investigation has ROI for the current mandate.
  2. Generate a dynamic DAG JSON payload with per-node cognitive profiles.
  3. Produce a confidence proof score used by N-Stroke autonomy gating.

This module is deterministic/offline-safe by default (no network calls).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine.model_garden import CognitiveProfile


@dataclass(frozen=True)
class GraphNodeSpec:
    """One executable node in the dynamic DAG."""

    node_id: str
    action_type: str
    dependencies: list[str]
    cognitive_profile: CognitiveProfile
    node_mandate: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "action_type": self.action_type,
            "dependencies": self.dependencies,
            "cognitive_profile": self.cognitive_profile.to_dict(),
            "node_mandate": self.node_mandate,
        }


@dataclass(frozen=True)
class DepthAssessment:
    investigation_roi: str   # high | medium | low
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "investigation_roi": self.investigation_roi,
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class ConfidenceProof:
    """How close this dynamic graph is to the autonomy confidence bar (0.99)."""

    historical_similarity: float
    topology_validity: float
    dry_run_readiness: float
    tribunal_cleanliness: float
    divergence_coverage: float
    convergence_guardrail: float  # ⭐ NEW: monitors healing loop safety
    reversibility_guarantees: float  # ⭐ NEW: atomic rollback capability
    proof_confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "historical_similarity": round(self.historical_similarity, 3),
            "topology_validity": round(self.topology_validity, 3),
            "dry_run_readiness": round(self.dry_run_readiness, 3),
            "tribunal_cleanliness": round(self.tribunal_cleanliness, 3),
            "divergence_coverage": round(self.divergence_coverage, 3),
            "convergence_guardrail": round(self.convergence_guardrail, 3),
            "reversibility_guarantees": round(self.reversibility_guarantees, 3),
            "proof_confidence": round(self.proof_confidence, 3),
        }


@dataclass(frozen=True)
class DynamicExecutionPlan:
    depth_assessment: DepthAssessment
    execution_graph: list[GraphNodeSpec]
    confidence_proof: ConfidenceProof

    def to_dict(self) -> dict[str, Any]:
        return {
            "depth_assessment": self.depth_assessment.to_dict(),
            "execution_graph": [n.to_dict() for n in self.execution_graph],
            "confidence_proof": self.confidence_proof.to_dict(),
        }


@dataclass(frozen=True)
class SwarmTopology:
    """Wave-plan for a Cognitive Swarm execution (FORK → SHARE)."""

    active_personas: list[str]
    # each wave is a list of {id, type} dicts
    waves: list[list[dict[str, str]]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_personas": self.active_personas,
            "waves": self.waves,
        }


class MetaArchitect:
    """Deterministic Meta-Architect for dynamic DAG generation."""

    _HIGH_ROI_HINTS = frozenset({
        "architecture", "refactor", "multi", "parallel", "security",
        "self-improvement", "dynamic", "pipeline", "model", "dag",
        "latency", "accuracy", "autonomous", "branch", "healing",
    })

    def generate(self, mandate_text: str, intent: str) -> DynamicExecutionPlan:
        roi = self._assess_roi(mandate_text)
        nodes = self._build_graph(mandate_text, intent, roi.investigation_roi)
        proof = self._build_confidence_proof(nodes, roi.investigation_roi)
        return DynamicExecutionPlan(
            depth_assessment=roi,
            execution_graph=nodes,
            confidence_proof=proof,
        )

    def to_topology_spec(self, plan: DynamicExecutionPlan) -> list[tuple[str, list[str]]]:
        """Convert execution_graph to TopologicalSorter-compatible spec."""
        return [(node.node_id, list(node.dependencies)) for node in plan.execution_graph]

    def _assess_roi(self, mandate_text: str) -> DepthAssessment:
        text = mandate_text.lower()
        hits = sum(1 for hint in self._HIGH_ROI_HINTS if hint in text)
        if hits >= 3 or len(text) > 320:
            return DepthAssessment(
                investigation_roi="high",
                rationale=(
                    "Mandate is complex/system-level; "
                    "deep research likely improves correctness."
                ),
            )
        if hits >= 1 or len(text) > 160:
            return DepthAssessment(
                investigation_roi="medium",
                rationale="Mandate has moderate complexity; selective deepening is beneficial.",
            )
        return DepthAssessment(
            investigation_roi="low",
            rationale="Mandate appears narrow; optimize for speed with minimal depth overhead.",
        )

    def _build_graph(self, mandate_text: str, intent: str, roi: str) -> list[GraphNodeSpec]:
        base: list[GraphNodeSpec] = []

        if roi == "high":
            base.append(GraphNodeSpec(
                node_id="deep_research",
                action_type="deep_research",
                dependencies=[],
                cognitive_profile=CognitiveProfile(
                    primary_need="synthesis",
                    minimum_tier=1,
                    lock_model=None,
                ),
                node_mandate=(
                    "Gather additional SOTA evidence and prior-art signals before design."
                ),
            ))

        pre_deps = ["deep_research"] if roi == "high" else []

        base.extend([
            GraphNodeSpec(
                node_id="audit_wave",
                action_type="audit_wave",
                dependencies=list(pre_deps),
                cognitive_profile=CognitiveProfile("reasoning", 2, None),
                node_mandate="Audit constraints, security risks, and invariants.",
            ),
            GraphNodeSpec(
                node_id="design_wave",
                action_type="design_wave",
                dependencies=["audit_wave"],
                cognitive_profile=CognitiveProfile("reasoning", 3, None),
                node_mandate="Produce concrete architecture blueprint and wave decomposition.",
            ),
            GraphNodeSpec(
                node_id="ux_eval",
                action_type="ux_eval",
                dependencies=["audit_wave"],
                cognitive_profile=CognitiveProfile("synthesis", 2, None),
                node_mandate="Define human-centric UX/accessibility constraints if relevant.",
            ),
            GraphNodeSpec(
                node_id="ingest",
                action_type="ingest",
                dependencies=["design_wave", "ux_eval"],
                cognitive_profile=CognitiveProfile("speed", 0, "local_slm"),
                node_mandate="Load and summarise the exact target files and context.",
            ),
            GraphNodeSpec(
                node_id="analyse",
                action_type="analyse",
                dependencies=["ingest"],
                cognitive_profile=CognitiveProfile("reasoning", 2, None),
                node_mandate="Root-cause and dependency analysis based on loaded context.",
            ),
            GraphNodeSpec(
                node_id="implement",
                action_type="implement",
                dependencies=["analyse"],
                cognitive_profile=CognitiveProfile("coding", 3, None),
                node_mandate=f"Implement changes for intent={intent} with deterministic behavior.",
            ),
            GraphNodeSpec(
                node_id="validate_primary",
                action_type="validate",
                dependencies=["implement"],
                cognitive_profile=CognitiveProfile("reasoning", 2, None),
                node_mandate="Primary validation: tests, invariants, and security boundaries.",
            ),
            GraphNodeSpec(
                node_id="validate_divergent",
                action_type="validate",
                dependencies=["implement"],
                cognitive_profile=CognitiveProfile("speed", 0, "local_slm"),
                node_mandate="Divergent validation: cheap independent checker for redundancy.",
            ),
            GraphNodeSpec(
                node_id="emit",
                action_type="emit",
                dependencies=["validate_primary", "validate_divergent"],
                cognitive_profile=CognitiveProfile(
                    "synthesis", 0, "local_slm"),
                node_mandate="Emit concise completion summary and next-step recommendation.",
            ),
        ])
        return base

    def _weight_swarm_hierarchy(self, mandate: str, intent: str) -> list[str]:
        """Determine the Dynamic Hierarchy of the Cognitive Swarm from context.

        Returns an ordered list of personas to spawn.  The Gapper always leads
        (strategy first); remaining personas are selected by intent heuristics.
        """
        mandate_lower = mandate.lower()
        swarm: list[str] = ["gapper"]  # always start with gap analysis

        if intent in ("IDEATE", "DESIGN", "SPAWN_REPO") or "new" in mandate_lower:
            swarm.extend(["innovator", "optimizer", "sustainer"])
        elif intent in ("DEBUG", "AUDIT") or any(
            kw in mandate_lower for kw in ("fix", "error", "bug", "broken")
        ):
            swarm.extend(["tester_stress", "optimizer", "sustainer"])
        elif any(
            kw in mandate_lower for kw in ("slow", "optimize", "latency", "performance")
        ):
            swarm.extend(["optimizer", "tester_stress"])
        else:
            # Balanced default swarm
            swarm.extend(["innovator", "optimizer",
                         "tester_stress", "sustainer"])

        return swarm

    def generate_swarm_topology(self, mandate: str, intent: str) -> SwarmTopology:
        """Generate a swarm-based FORK → SHARE wave plan for the N-Stroke Engine.

        Wave 1:  Gapper defines strategy (serial — must run first).
        Wave 2:  Parallel swarm execution via BranchExecutor FORK.
        Wave 3:  16D convergence / synthesis node.
        """
        active_personas = self._weight_swarm_hierarchy(mandate, intent)

        waves: list[list[dict[str, str]]] = [
            # Wave 1 — strategic analysis
            [{"id": "node-gap", "type": "gapper"}],
            # Wave 2 — parallel swarm (all personas except gapper)
            [
                {"id": f"node-{p}", "type": p}
                for p in active_personas
                if p != "gapper"
            ],
            # Wave 3 — 16D synthesis / convergence gate
            [{"id": "node-16d-synthesis", "type": "validate_16d"}],
        ]

        return SwarmTopology(active_personas=active_personas, waves=waves)

    def _build_confidence_proof(self, nodes: list[GraphNodeSpec], roi: str) -> ConfidenceProof:
        node_ids = {n.node_id for n in nodes}
        has_divergence = "validate_primary" in node_ids and "validate_divergent" in node_ids
        has_discovery = "audit_wave" in node_ids and "design_wave" in node_ids
        has_healing_guards = has_divergence  # Divergence allows healing to converge

        # Core proof components
        historical_similarity = 0.97 if roi == "high" else 0.95
        topology_validity = 1.0 if has_discovery else 0.8
        dry_run_readiness = 0.99 if "implement" in node_ids else 0.9
        tribunal_cleanliness = 0.99

        # ⭐ NEW: Divergence coverage (multi-model voting increases convergence certainty)
        divergence_coverage = 1.0 if has_divergence else 0.7

        # ⭐ NEW: Convergence guardrail (is the healing loop safe from infinite loops?)
        # High ROI + divergence = system can measure correctness and abort if looping
        convergence_guardrail = 0.95 if has_healing_guards and roi in (
            "high", "medium") else 0.75

        # ⭐ NEW: Reversibility guarantees (can every change be rolled back atomically?)
        # All nodes must respect the engine/ boundary (writes only to own components)
        reversibility_guarantees = 0.98 if "emit" in node_ids else 0.85

        # Composite confidence: weighted average of all 7 dimensions
        # Target: 0.99 for autonomous execution, else emit consultation_recommended
        proof_confidence = min(
            1.0,
            0.14 * historical_similarity
            + 0.14 * topology_validity
            + 0.14 * dry_run_readiness
            + 0.12 * tribunal_cleanliness
            + 0.14 * divergence_coverage
            + 0.13 * convergence_guardrail
            + 0.19 * reversibility_guarantees,  # Highest weight: rollback safety
        )

        return ConfidenceProof(
            historical_similarity=historical_similarity,
            topology_validity=topology_validity,
            dry_run_readiness=dry_run_readiness,
            tribunal_cleanliness=tribunal_cleanliness,
            divergence_coverage=divergence_coverage,
            convergence_guardrail=convergence_guardrail,
            reversibility_guarantees=reversibility_guarantees,
            proof_confidence=proof_confidence,
        )
