# TooLoo V4 Sovereign System Mapping

This document provides a comprehensive map of the **TooLoo V4 Sovereign Hub** (Version 4.2.0), detailing its components, features, and constitutional alignment.

---

## 1. 4D Cognitive Architecture Overview
TooLoo V4 is built on a **Sovereign-Federated model** where a central **Cognitive Kernel** orchestrates specialized **Organs** using the **Model Context Protocol (MCP)**. The system is governed by a **12-Rule Constitution** (`GEMINI.md`) that enforces operational discipline, architectural purity, and autonomous self-healing.

### The Standard Pulse
- **Rule 10 (Stamping)**: Every action and state change is 6W-stamped (Who, What, Where, When, Why, How).
- **Rule 13 (Decoupling)**: Organs are physically decoupled and communicate via standardized JSON-RPC (MCP) or REST.

---

## 2. Component Map

### 2.1 The Cognitive Kernel (`tooloo_v4_hub/kernel`)
The brain of the system, responsible for orchestration and governance.
- **`mcp_nexus.py`**: The Active Nerve Center. Manages the lifecycle of all federated organs. Switches between local subprocesses and remote REST tethers based on environment.
- **`orchestrator.py`**: Dispatches missions and manages high-level goal execution via the **Mega DAG**.
- **`cognitive/chat_engine.py`**: The reasoning layer. Handles parallel triangulation, JIT context injection, and consensus validation.
- **`governance/living_map.py`**: Tracks the structural health and manifest of the entire codebase.
- **`governance/sota_benchmarker.py`**: Evaluates system performance against State-Of-The-Art (SOTA) standards.
- **`reality_check/GRAND_CALIBRATION_PULSE.py`**: Autonomously refines the system based on empirical benchmarks.

### 2.2 Federated Organs (`tooloo_v4_hub/organs`)
Autonomous specialized services tethered to the Nexus.
- **Memory Organ**:
    - `memory_logic.py`: Handles multi-tier memory (Fast, Medium, Long) with autonomous transcript compaction (Rule 9).
    - `sqlite_persistence.py`: Local-tier storage.
    - `firestore_persistence.py`: Cloud-native storage.
- **Audio Organ (Claudio)**:
    - Provides high-fidelity acoustic processing and spectral identity management.
- **Vertex AI Organ**:
    - Integration with Google Cloud Vertex AI for SOTA embeddings (`text-embedding-004`) and Model Garden access.
- **Circus Spoke**:
    - The visualization and UI transport layer (WebGL/Three.js integration).
- **System Organ**:
    - Local OS-level capabilities (file system, process management).

---

## 3. Deployment Strategy (Local vs. Cloud)

The system automatically adapts its behavior based on the environment to maximize stability and minimize latency.

| Feature | Local Environment (`CLOUD_NATIVE=false`) | Cloud Run (`CLOUD_NATIVE=true`) |
| :--- | :--- | :--- |
| **Organ Tethering** | **Subprocess**: Uses `stdio` transport. | **REST/SSE**: Dispatches to remote endpoints. |
| **Wake Logic** | **Eager**: All organs initialized on start. | **Lazy-Wake**: Organs awaken JIT (Rule 18). |
| **Persistence** | **SQLite**: Local `.db` files. | **Firestore/GCS**: Fully managed NoSQL storage. |
| **Embeddings** | **Heuristic**: Positional TF-IDF (no cost). | **Vertex AI**: SOTA semantic embeddings. |
| **Security** | Local environment variables. | **Google Cloud KMS**: Enclave-level secrets. |
| **Stability** | Standard asyncio loop. | **LEAN_MODE**: Proactively sheds luxury features. |

---

## 4. Feature Inventory

### 4.1 Cognitive & Reasoning
- **Parallel Triangulation**: Queries multiple LLM providers (Vertex, OpenAI, Anthropic) to reach consensus.
- **JIT Context Injection**: Dynamically builds the perfect prompt context from the Memory Organ.
- **Consensus Validation (Rule 1)**: Vetoes responses that violate the Sovereign Constitution.

### 4.2 Operational & Self-Healing
- **Missions (`tooloo_v4_hub/missions`)**: Task-specific autonomous units.
  - `grand_convergence_mission`: Orchestrates multi-organ alignment.
  - `memory_training_mission`: Refines the SOTA vector search based on interaction.
  - `mission_claudio_grounding`: Syncs acoustic data with architectural designs.
  - `mission_introspect`: Self-diagnostic and Rule 7 enforcement.
- **Ouroboros Loop**: A 5-minute background pulse that detects architectural drift and performs self-repairs.
- **SOTA Pulse**: Weekly refresh of the Model Garden Registry to keep the system at peak performance.
- **Recovery Pulse**: OS-level checkpointing to resume missions after crashes or cold starts.
- **Transcript Compaction**: Migrates "Fast" session memory into "Long" architectural memory (Rule 9).

### 4.3 Governance & SVI
- **Crucible Validator**: A blocking gate that verifies mission plans against security and design guardrails.
- **Sovereign Vitality Index (SVI)**: A real-time metric (0.00 - 1.00) representing system health and constitutional purity.

---

## 5. Registry Inventory (Metadata-First)
Per Rule 1, capabilities are treated as data.

- **`CommandRegistry`**: User-facing commands for the Sovereign Portal and CLI.
- **`CognitiveRegistry`**: Internal model-facing tools for reasoning and orchestration.
- **`SOTA Registry`**: Defines the benchmarks for system performance.
- **`Model Garden Registry`**: Lists available AI models and their performance metrics.
- **`Material Registry` (V4 PBR)**: Found in `circus_spoke`, defines physical properties for 3D manifestations.

---

## 6. Data & Persistence Map

| Sector | Local Path | Cloud Target |
| :--- | :--- | :--- |
| **Chat History** | `psyche_bank/chat_history.db` | Firestore: `too-loo-chat` |
| **Fast Memory** | `psyche_bank/fast_memory.json` | Firestore: `psyche_fast` |
| **Engrams** | `psyche_bank/learned_engrams.json`| `gcs_repository.py` (Bucket Ops) |
| **Vector Store** | `psyche_bank/vector_store.json` | Managed Vertex AI Vector Search |
| **Audit Logs** | `hub.log` | Cloud Logging (Stackdriver) |

---

> [!NOTE]
> This system mapping is a living document. Any structural changes to the Hub must be reflected here as part of the **Rule 7 (Architectural Integrity)** maintenance cycle.
