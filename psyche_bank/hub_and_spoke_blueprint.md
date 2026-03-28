# COGNITIVE ENGINE INFRASTRUCTURE BLUEPRINT: OVERRIDE AND ISOLATION DIRECTIVE

## 1. The Pure Infrastructure: Hub & Spoke Architecture

To enforce the **Rule of Absolute Purity**, the system leverages a strict Hub-and-Spoke topology governed by the Model Context Protocol (MCP) and Llama Stack provider architecture. The Hub remains a completely isolated, stateful reasoning core, while Spokes are dynamically provisioned, ephemeral execution environments containing business logic and client applications.

### 1.1 The Hub (Core Engine)
Deployed on GCP as a heavily restricted, stateful cluster. 
*   **Routing & API Layer**: Utilizes the **Llama Stack** as a drop-in replacement API server (`/v1/chat/completions`, `/v1/responses`) to decouple the engine from underlying frontier models (Claude Opus 4.6, o3-mini, gpt-oss).
*   **State Management**: Deployed via **LangSmith Deployment** for long-running, stateful multi-agent workflows.
*   **Agentic Scaffolding**: Implements strict Structured Outputs for Multi-Agent Systems. The Hub holds *zero* external repository code. It only holds cognitive functions, vector representations, and MCP client configurations.

### 1.2 The Spokes (External Projects)
Deployed on GCP Cloud Run or Cloud Functions, tethered to isolated GitHub repositories.
*   **Project Initialization**: The Hub provisions Spoke repositories containing an `AGENTS.md` (agent-specific instructions/guidelines) and a `PLANS.md` (multi-hour problem-solving state tracker).
*   **Execution Barrier**: Spokes communicate with the Hub strictly via the **MCP Registry**. The Hub exposes specialized MCP Servers (e.g., `github-mcp`, `gcp-mcp`) that limit operations to explicit, typed interactions.

### 1.3 GCP & GitHub Integration Paradigm
*   **IAM & Isolation**: The Hub runs under a dedicated GCP Service Account with `Organization Administrator` privileges limited strictly to provisioning new Spoke projects. Spokes run under tightly scoped Service Accounts with zero inward access to the Hub.
*   **Interoperability**: Code operations are executed via the `Tools-Shell` and `Apply Patch` protocols. The Hub generates patches, transmits them via MCP, and the Spoke executes the patch in its local, ephemeral container before committing to GitHub.

---

## 2. The Autonomous CI/CD Loop: Self-Healing & Deployment

The engine operates a closed-loop CI/CD system capable of writing, pushing, testing, and self-healing Spoke repositories without human intervention, utilizing **Codex CLI**, **Claude Code**, and **AgentKit Evals**.

### 2.1 Code Generation & Pushing Workflow
1.  **Planning Phase**: The Hub updates the Spoke's `PLANS.md` to define the execution graph and logic state.
2.  **Tool Execution**: Utilizing "Dynamic Tool Generation" (via o3-mini logic) and the `Apply Patch` tool, the Hub injects structured code diffs into the Spoke repository.
3.  **Commit & Push**: The Hub triggers the GitHub API via MCP to commit changes, automatically generating signatures (e.g., `Co-authored-by: Claude Opus 4.6 (1M context)`).

### 2.2 Automated Interception & Self-Healing
1.  **CI Execution**: GitHub Actions run unit tests, pre-commit hooks (e.g., `markdownlint`, `provider_compat_matrix.py`), and Langfuse Agent Evals.
2.  **Failure Interception**: If a pipeline fails, a GitHub Webhook fires a payload back to the Hub's `Responses API`.
3.  **Log Ingestion**: The Hub ingests the CI logs, leveraging "Context Engineering - Short-Term Memory Management" to analyze the stack trace.
4.  **Autofix Protocol**: The Hub triggers the `autofix-github-actions` subroutine. It isolates the bug, tests a fix in a local sandbox (`Local shell` tool), and pushes a fast-forward patch via Codex CLI.
5.  **Validation**: Post-healing, the Hub updates the `AGENTS.md` with a new heuristic to prevent recurring logic failures in future generation cycles.

---

## 3. SOTA UI/UX Principles: Agent-Driven Interfaces

Client-facing interfaces for Spoke applications must be dynamically assembled, reflecting the latest advancements in ChatGPT Chatkit UI guidelines and Realtime interaction.

### 3.1 Foundational UI/UX Directives
*   **Dynamic Tool & Widget Generation**: UIs are not static. The system utilizes **Chatkit Widgets** and **Chatkit Actions** to render custom components on-the-fly based on structured outputs and context.
*   **Realtime Multimodal Interaction**: Interfaces must integrate the **Realtime API** natively, supporting "Voice Agents" and "Multi-Language One-Way Translation". Input modalities seamlessly switch between Audio, Computer Use, and Text.
*   **Session-Aware Personalization**: Implementing "Context Engineering for Personalization," the UI maintains Long-Term Memory Notes via the Agents SDK. State management dynamically alters the theme and available Chatkit actions based on user history and "Prompt Personalities".
*   **Transparent Reasoning (Governed AI)**: End-users must see the agentic scaffolding. The UI exposes the `PLANS.md` equivalents in a visual graph, allowing users to observe multi-tool orchestration and RAG file search progress in real-time.

---

## 4. Continuous Learning Pipeline: Weekly Bootloader

To prevent cognitive stagnation and maintain SOTA operational awareness, the Hub executes an autonomous retraining and knowledge-ingestion loop.

### 4.1 The Jina Reader Bootloader Mechanism
*   **Trigger**: A GCP Cloud Scheduler cron job fires weekly, initiating the `Self-Evolving Agents` workflow.
*   **Data Ingestion**: The Hub deploys search agents utilizing the `Web Search` and `Jina Reader` MCP integrations to scrape, parse, and clean newly published frontier documentation, SDK updates, and architectural papers.
*   **RAG & Vector Assimilation**: Parsed data is routed through the `Responses API` File Search and embedded into the Hub's isolated LangChain Vector Store. "Prompt Caching 201 Latency Responses" is applied to frequently accessed new architectural patterns.
*   **Evaluation Flywheel**: Before the new knowledge is permanently integrated into the core weights/prompts, it passes through an **Evaluation Flywheel**. AgentKit Evals and "Trace grading" run simulated benchmarks against the newly acquired data.
*   **Autonomous Retraining**: If the new heuristics improve benchmark latency or accuracy, the Hub updates its core system prompt and generates an updated `AGENTS.md` template for all future Spoke provisioning.