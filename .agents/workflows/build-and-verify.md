---
description: How to build and verify features for the Tooloo V4.2 Sovereign Hub.
---

# Build-And-Verify Protocol (BAVP) v4.2

This workflow is the standard for **Meso-Scale** feature development. 

## 1. Plan (Pulse 1)
- Identify the feature or bug.
- Define the **Vision** and **Success Criteria**.
- Trigger **Academy Ingestion** (`KnowledgeGateway`) to ensure SOTA alignment.
- Create/Update the **Implementation Plan**.

## 2. Manifest (Pulse 2: SMP Matrix)
- Use **Matrix Decomposition** to generate the implementation tree.
- Simulate with **Digital Twin**.
- Execute parallel manifestation of components.

## 3. Ground (Pulse 3: Verification)
- Run unit tests in `tooloo_v4_hub/tests/`.
- Run the **Sovereign Readiness Audit** (`sovereign_readiness_audit.py`).
- Run the **Grounding & Retrieval Eval Pulse** (`tests/eval_pulse.py`) using LLM-as-a-Judge.
- Perform **Reality Checks** in `tooloo_v4_hub/kernel/reality_check/`.

## 4. Calibrate (Pulse 4: Rule 16)
- Calculate the **ValueScore**.
- Compare outcomes against the plan.
- Update the **Walkthrough** and **Task** artifacts.

---

### Command Palette (V4.2 Shortcuts)
- **Map Ecosystem**: `grep -r "TODO" tooloo_v4_hub`
- **Audit Purity**: `python3 tooloo_v4_hub/kernel/constitution_audit.py`
- **Stress Test**: `python3 tooloo_v4_hub/kernel/reality_check/SUPER_STRESS_TEST_V3.py`
