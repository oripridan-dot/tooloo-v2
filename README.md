# TooLoo V3: Pure Sovereign Cognitive Hub

Welcome to the **Sovereign Pure** architecture. This repository represents the total decoupling of reasoning from execution, achieving 100% purity and 6W-stamped verification.

## 🏛️ Architecture: Hub & Organ Cluster

The TooLoo V3 system is divided into a central Hub and a federated cluster of Organs and Spokes.

### 1. The Hub Kernel (`tooloo_v3_hub/kernel/`)
The Kernel is the stateless reasoning brain of the system.
- `kernel/stamping.py`: Mandatory bit-perfect 6W-Protocol.
- `kernel/mcp_nexus.py`: Secure conduit to all external Organs.
- `kernel/orchestrator.py`: Orchestrates multi-agent DAGs without local execution.

### 2. The Sovereign Bank (`tooloo_v3_hub/psyche_bank/`)
Isolated metadata and weights that define the Hub's identity.
- `psyche_bank/world_model_v3.json`: 22D Surrogate World Model weights.
- `psyche_bank/engram_registry.json`: Record of strategic outcomes.

### 3. Federated Organs (External)
Organs are independent services tethered via MCP.
- **Memory Organ**: Distributed Vector & Graph stores.
- **Audio Organ (Claudio)**: Native C++ DSP & Synthesis.

## 🚀 Getting Started

To initialize the V3 Hub and start the Sovereign reasoning loop:

```bash
python -m tooloo_v3_hub.main
```

## 📜 The Sovereign Protocol (6W)

Every cognitive acts is stamped with:
- **WHO**: The originating agent.
- **WHAT**: The specific action or intent.
- **WHERE**: The logical sector.
- **WHEN**: ISO-Timestamp.
- **WHY**: The teleological goal.
- **HOW**: The procedural strategy.

---

## 🏛️ Historical Archive
Legacy V2 components (the transitional `engine/` monolith) have been safely migrated to `archive/tooloo-v2-legacy/`.
