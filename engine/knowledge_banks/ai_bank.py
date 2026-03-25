"""
engine/knowledge_banks/ai_bank.py — SOTA Artificial Intelligence Knowledge Bank.

Covers model architectures, training paradigms, inference optimisation,
multi-agent systems, AI safety, LLM tooling, and the 2026 SOTA landscape.
"""
from __future__ import annotations

from pathlib import Path

from engine.knowledge_banks.base import KnowledgeBank, KnowledgeEntry

_DEFAULT_PATH = (
    Path(__file__).resolve().parents[3] / "psyche_bank" / "ai.cog.json"
)


class AIBank(KnowledgeBank):
    """Curated AI/ML knowledge: transformer basics to agent-native 2026 SOTA."""

    def __init__(self, path: Path | None = None, bank_root: Path | None = None) -> None:
        if bank_root is not None:
            path = bank_root / "ai.cog.json"
        super().__init__(path or _DEFAULT_PATH)

    @property
    def bank_id(self) -> str:
        return "ai"

    @property
    def bank_name(self) -> str:
        return "AI Bank — Foundations to SOTA 2026"

    @property
    def domains(self) -> list[str]:
        return [
            "foundations",
            "llm_architecture",
            "training",
            "inference",
            "agents",
            "multimodal",
            "safety_alignment",
            "evaluation",
            "tools_ecosystem",
            "edge_inference",
        ]

    def _seed(self) -> None:
        entries = [
            # ── Foundations ────────────────────────────────────────────────────
            KnowledgeEntry(
                id="ai_found_attention",
                title="Scaled Dot-Product Attention: The Core Primitive",
                body="Attention(Q,K,V) = softmax(QKᵀ/√d_k)V. All transformer variants are built on this primitive. Flash Attention 3 fuses kernels to achieve near-memory-bandwidth-bound performance, reducing memory from O(N²) to O(N). Understanding this is prerequisite for any LLM work.",
                domain="foundations",
                tags=["attention", "transformer",
                      "flashattention", "QKV", "architecture"],
                relevance_weight=0.97,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="ai_found_scaling_laws",
                title="Neural Scaling Laws (Chinchilla Optimal)",
                body="Chinchilla laws: compute-optimal training uses ~20 tokens per parameter. Modern LLMs (Llama 3, Gemini 2.5) train over-token'd models (>100 tokens/param) to optimise inference cost over training cost. Scaling laws now include data quality as a first-class variable.",
                domain="foundations",
                tags=["scaling-laws", "Chinchilla",
                      "training", "compute", "efficiency"],
                relevance_weight=0.93,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="ai_found_emergent",
                title="Emergent Capabilities at Scale",
                body="Capabilities (multi-step reasoning, code synthesis) emerge discontinuously at specific scale thresholds. Chain-of-Thought (CoT) is reliable at 100B+ parameters. Few-shot learning quality scales with context window utilisation. Emergence is NOT well-predicted by interpolation.",
                domain="foundations",
                tags=["emergence", "scale", "chain-of-thought",
                      "few-shot", "reasoning"],
                relevance_weight=0.91,
                sota_level="foundational",
            ),
            # ── LLM Architecture ───────────────────────────────────────────────
            KnowledgeEntry(
                id="ai_llm_moe",
                title="Mixture of Experts (MoE): Sparse Activation",
                body="MoE routes each token to K of N expert feed-forward networks (typically K=2, N=8 or N=64). Doubles parameter count with only 1.25× compute cost. Gemini 1.5/2.5, GPT-4, Mixtral, and DeepSeek-V3 use MoE. Key trade-off: higher memory footprint vs. compute efficiency.",
                domain="llm_architecture",
                tags=["MoE", "sparse", "routing", "experts", "efficiency"],
                relevance_weight=0.93,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_llm_long_context",
                title="Long Context Windows: 1M+ Token Models",
                body="Gemini 2.5 Pro supports 1M+ tokens; Claude 3.5 Sonnet 200K. RoPE positional encoding with θ-scaling + sliding window attention enables efficient long-context inference. RAG is now complementary (not replacement) to long-context — use RAG for dynamic data, long context for deep analysis.",
                domain="llm_architecture",
                tags=["context-window", "long-context",
                      "RoPE", "RAG", "Gemini"],
                relevance_weight=0.95,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_llm_reasoning_models",
                title="Reasoning Models: o3, Gemini Thinking, DeepSeek-R1",
                body="Extended Thinking / Chain-of-Thought models allocate additional compute at inference time for multi-step reasoning. o3, Gemini 2.5 Flash Thinking, and DeepSeek-R1 achieve SOTA on math/code benchmarks. Trade-off: 3–10× latency increase for significantly harder tasks.",
                domain="llm_architecture",
                tags=["reasoning", "CoT", "o3",
                      "Gemini-thinking", "DeepSeek-R1"],
                relevance_weight=0.96,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_llm_multimodal_native",
                title="Natively Multimodal Architectures",
                body="2026 SOTA models process text, code, images, audio, and video natively (not via adapters). Gemini 2.0/2.5, GPT-4o, and Claude 3.5 are natively multimodal. Video understanding (1-hour+ temporal reasoning) is the 2026 frontier. Multimodal models outperform unimodal specialists on cross-modal tasks.",
                domain="llm_architecture",
                tags=["multimodal", "vision", "audio",
                      "video", "Gemini", "native"],
                relevance_weight=0.94,
                sota_level="sota_2026",
            ),
            # ── Training ───────────────────────────────────────────────────────
            KnowledgeEntry(
                id="ai_training_rlhf_rlaif",
                title="RLHF → RLAIF: AI Feedback Replaces Human Labels",
                body="RLAIF (Reinforcement Learning from AI Feedback) uses a stronger model to generate preference labels, scaling RLHF beyond human annotation capacity. Constitutional AI (Anthropic) extends this with explicit value principles. DPO (Direct Preference Optimisation) eliminates the RL step for alignment fine-tuning.",
                domain="training",
                tags=["RLHF", "RLAIF", "DPO", "alignment", "Constitutional-AI"],
                relevance_weight=0.91,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_training_lora",
                title="LoRA / QLoRA: Parameter-Efficient Fine-Tuning",
                body="LoRA decomposes weight updates into low-rank matrices (rank 4–64), reducing trainable parameters by 10,000×. QLoRA adds 4-bit quantisation (NF4), enabling 65B fine-tuning on a single 48GB GPU. PEFT with LoRA adapters is the 2026 standard for domain adaptation.",
                domain="training",
                tags=["LoRA", "QLoRA", "fine-tuning", "PEFT", "quantisation"],
                relevance_weight=0.92,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_training_synthetic_data",
                title="Synthetic Data: Models Training Models",
                body="High-quality synthetic data generation (Phi-3, Llama-3 pipeline) via stronger teacher models now matches or exceeds curated human data for many tasks. Key techniques: persona simulation, backtranslation, Evol-Instruct, and self-play. Data quality filtering (DSIR, IFD) is as critical as generation.",
                domain="training",
                tags=["synthetic-data", "Phi-3", "self-play",
                      "Evol-Instruct", "data-quality"],
                relevance_weight=0.90,
                sota_level="sota_2026",
            ),
            # ── Inference ──────────────────────────────────────────────────────
            KnowledgeEntry(
                id="ai_inference_speculative",
                title="Speculative Decoding: 2–3× Faster Inference",
                body="A small draft model proposes N tokens; the large verifier model checks all in one forward pass. Produces correct output with 2–3× the throughput. Medusa extends this with multiple independent heads. Standard in vLLM, TGI, and SGLang production deployments.",
                domain="inference",
                tags=["speculative-decoding", "inference",
                      "throughput", "vLLM", "Medusa"],
                relevance_weight=0.90,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_inference_quantisation",
                title="INT4/INT8 Quantisation: Production-Ready Compression",
                body="GPTQ, AWQ, and bitsandbytes provide lossless-equivalent INT4 quantisation for most tasks. INT4 models run at 4× the token throughput with <1% quality degradation on benchmarks. GGUF + llama.cpp enables edge deployment. ExLlama2 is the fastest local inference backend for NVIDIA GPUs.",
                domain="inference",
                tags=["quantisation", "INT4", "GPTQ",
                      "AWQ", "llama.cpp", "GGUF"],
                relevance_weight=0.91,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_inference_batch_serving",
                title="Continuous Batching + PagedAttention (vLLM)",
                body="vLLM's PagedAttention manages KV-cache as virtual memory pages, eliminating fragmentation and enabling continuous batching. Achieves 24× higher throughput than naive serving. SGLang with RadixAttention improves prefix caching for multi-turn agents. Both are production-standard in 2026.",
                domain="inference",
                tags=["vLLM", "PagedAttention",
                      "continuous-batching", "KV-cache", "serving"],
                relevance_weight=0.92,
                sota_level="sota_2026",
            ),
            # ── Agents ─────────────────────────────────────────────────────────
            KnowledgeEntry(
                id="ai_agents_tool_use",
                title="Tool Use (Function Calling): The Agent Primitive",
                body="All frontier models support structured function calling (OpenAI tool_calls format, Gemini function_declarations). JSON Schema defines tool inputs/outputs. Parallel tool calls (multiple tools in one pass) are natively supported in GPT-4o, Gemini 2.0+, and Claude 3.5. Use this over text parsing.",
                domain="agents",
                tags=["tool-use", "function-calling",
                      "JSON-schema", "parallel-tools", "agent"],
                relevance_weight=0.95,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_agents_react_pattern",
                title="ReAct: Reasoning + Acting Pattern",
                body="ReAct interleaves Thought → Action → Observation loops. More reliable than raw chain-of-thought for tool-use tasks. Variants: ReWOO (parallel planning), LATS (tree search), and Reflexion (self-correction). LangGraph and LlamaIndex AgentWorkflow implement these as DAGs.",
                domain="agents",
                tags=["ReAct", "reasoning", "tool-use",
                      "LangGraph", "agent-loop"],
                relevance_weight=0.93,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_agents_multi_agent",
                title="Multi-Agent Systems: Orchestrator + Specialist Pattern",
                body="Orchestrator agent decomposes tasks and delegates to specialist agents (coder, researcher, critic). AutoGen, CrewAI, and Google Agent Development Kit (ADK) implement this. Key design: agents communicate via structured messages, not free-form text. Shared blackboard prevents state divergence.",
                domain="agents",
                tags=["multi-agent", "orchestrator",
                      "AutoGen", "CrewAI", "ADK", "specialist"],
                relevance_weight=0.94,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_agents_memory_architecture",
                title="Agent Memory: In-Context, External, and Episodic",
                body="Three memory tiers: in-context (current window), external (vector DB + structured DB), episodic (compressed summaries of past interactions). Agent memory systems (MemGPT, Zep, Letta) manage tiers automatically. Episodic memory is the 2026 frontier for long-running agents.",
                domain="agents",
                tags=["memory", "vector-DB", "episodic",
                      "MemGPT", "context-management"],
                relevance_weight=0.92,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_agents_mcp_protocol",
                title="Model Context Protocol (MCP): Standard Tool Interface",
                body="MCP (Anthropic, 2024–2026) is the emerging standard for connecting LLMs to tools and data sources. Defines resources, tools, and prompts as first-class primitives. Supported by Claude, Cursor, and major IDEs. Replaces bespoke tool integration with a typed, discoverable protocol.",
                domain="agents",
                tags=["MCP", "tool-protocol", "Claude",
                      "Cursor", "standard", "tool-use"],
                relevance_weight=0.96,
                sota_level="sota_2026",
            ),
            # ── Safety & Alignment ─────────────────────────────────────────────
            KnowledgeEntry(
                id="ai_safety_jailbreak",
                title="Jailbreak & Prompt Injection: The Primary AI Runtime Threat",
                body="Prompt injection attacks embed adversarial instructions in tool outputs, retrieved documents, or user input. Defences: input/output filters (Llama Guard 3), structured output (JSON schema enforcement), separate trust levels for system vs user vs tool messages. OWASP LLM Top 10 v1.1 ranks this #1.",
                domain="safety_alignment",
                tags=["safety", "prompt-injection",
                      "jailbreak", "Llama-Guard", "OWASP-LLM"],
                relevance_weight=0.97,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_safety_hallucination",
                title="Hallucination Mitigation: Grounding and Verification",
                body="Hallucination mitigation stack: RAG for factual grounding, citation-required prompts, self-consistency sampling (majority vote across N completions), and external verification via tools or search. Chain-of-verification (CoVe) prompts the model to cross-check its own claims. No method eliminates hallucinations; multiple layers are required.",
                domain="safety_alignment",
                tags=["hallucination", "grounding",
                      "RAG", "self-consistency", "CoVe"],
                relevance_weight=0.95,
                sota_level="sota_2026",
            ),
            # ── Evaluation ─────────────────────────────────────────────────────
            KnowledgeEntry(
                id="ai_eval_llm_as_judge",
                title="LLM-as-Judge Evaluation: Scalable Quality Assessment",
                body="Using a strong LLM (GPT-4o, Gemini 2.5 Pro) as an evaluator scores model outputs on rubrics (accuracy, helpfulness, safety). MT-Bench, Arena Hard, and WildBench use this approach. Bias mitigation: evaluator shouldn't know which model produced which response (blind evaluation).",
                domain="evaluation",
                tags=["evaluation", "LLM-judge",
                      "MT-Bench", "quality", "rubrics"],
                relevance_weight=0.90,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_eval_benchmarks_2026",
                title="2026 Key Benchmarks: MMMU-Pro, SWE-bench, HumanEval+",
                body="MMMU-Pro (multimodal reasoning), SWE-bench Verified (real GitHub issues), and HumanEval+ (harder code synthesis) are the gold standards in 2026. Chatbot Arena (LMSYS) remains the best real-user preference signal. LiveBench prevents contamination with monthly-updated questions.",
                domain="evaluation",
                tags=["benchmarks", "SWE-bench",
                      "MMMU-Pro", "Arena", "LiveBench"],
                relevance_weight=0.89,
                sota_level="sota_2026",
            ),
            # ── Tools Ecosystem ────────────────────────────────────────────────
            KnowledgeEntry(
                id="ai_tools_langchain_evolution",
                title="LangChain → LangGraph: Stateful Agent Orchestration",
                body="LangGraph replaced LangChain chains with explicit state graphs (nodes + edges + state schema). Enables complex multi-step agent loops with human-in-the-loop, persistence, and time-travel debugging. LangSmith provides traces and evals. 2026 production-standard for complex agentic pipelines.",
                domain="tools_ecosystem",
                tags=["LangGraph", "LangChain",
                      "orchestration", "state-machine", "agents"],
                relevance_weight=0.91,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_tools_vector_dbs",
                title="Vector Databases: Pgvector vs Dedicated Stores",
                body="pgvector (PostgreSQL extension) covers 80% of RAG use cases with HNSW indexing and hybrid search. For scale (>10M vectors) or multimodal: Weaviate, Qdrant, or Pinecone. Embed with text-embedding-3-large (OpenAI) or Gemini gemini-embedding-001 (best multilingual). Cohere Embed v3 leads on retrieval benchmarks.",
                domain="tools_ecosystem",
                tags=["vector-DB", "pgvector", "Qdrant",
                      "embeddings", "RAG", "HNSW"],
                relevance_weight=0.92,
                sota_level="sota_2026",
            ),
            # ── Edge Inference ─────────────────────────────────────────────────
            KnowledgeEntry(
                id="ai_edge_webnn",
                title="WebNN + ONNX Runtime Web: Browser AI Inference",
                body="WebNN (W3C API) provides hardware-accelerated neural network inference in browsers via GPU/NPU. ONNX Runtime Web with WebNN backend achieves near-native speeds for models <500M params. Transformers.js 3.x wraps this for high-level browser inference. Ship quantised ONNX models (INT8/INT4) via CDN.",
                domain="edge_inference",
                tags=["WebNN", "ONNX", "browser",
                      "edge", "Transformers.js", "WebGPU"],
                relevance_weight=0.88,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="ai_edge_slm",
                title="Small Language Models (SLMs): Sub-10B On-Device",
                body="Phi-4 (14B), Gemma 3 (4B/12B), and Llama 3.2 (1B/3B) deliver near-frontier quality on-device. Quantised to 4-bit and running on Apple Neural Engine, Snapdragon NPU, or MediaTek. Enables offline AI, privacy-preserving inference, and sub-10ms latency. SLMs are the 2026 edge-AI standard.",
                domain="edge_inference",
                tags=["SLM", "Phi-4", "Gemma",
                      "on-device", "quantisation", "edge"],
                relevance_weight=0.90,
                sota_level="sota_2026",
            ),
        ]
        for e in entries:
            self._store.entries.append(e)
