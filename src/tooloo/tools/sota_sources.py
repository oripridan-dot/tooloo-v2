"""
SOTA Data Sources Registry
WHO: TooLoo Sovereign Hub
WHAT: Curated, domain-partitioned registry of trusted data sources for JIT enrichment.
WHY: Rule 0 — Ground all reasoning in real, verifiable data. No fabrication.

Three tiers:
  INTERNAL  — system-local knowledge (KnowledgeBank, core_fs scan, project README)
  WEB_SOTA  — curated trusted web sources partitioned by domain
  LIVE      — real-time queryable endpoints (requires API key or network access)

Providers: OpenAI, Google/DeepMind, Anthropic, NVIDIA, DeepSeek, Zhipu AI,
           xAI (Grok), Mistral AI, Meta AI, Cohere, Together AI + domain authorities.
"""

from typing import Dict, List, Any

# ---------------------------------------------------------------------------
# WEB_SOTA_SOURCES: Canonical trusted sources, partitioned by domain.
# Used by SotaJitOperator to select the right source before enriching a node.
# ---------------------------------------------------------------------------
WEB_SOTA_SOURCES: Dict[str, List[Dict[str, str]]] = {

    # -------------------------------------------------------------------------
    # AI RESEARCH — foundational AI lab docs, model papers, research blogs
    # -------------------------------------------------------------------------
    "ai_research": [
        # Anthropic
        {"name": "Anthropic Docs", "url": "https://docs.anthropic.com", "focus": "Claude API, tool use, extended thinking, prompt engineering, vision, streaming"},
        {"name": "Anthropic Cookbook", "url": "https://github.com/anthropics/anthropic-cookbook", "focus": "Practical Claude code recipes, RAG, tool use patterns"},
        {"name": "Anthropic Prompt Library", "url": "https://docs.anthropic.com/en/prompt-library", "focus": "Curated, tested system prompts for common tasks"},
        # OpenAI
        {"name": "OpenAI Platform Docs", "url": "https://platform.openai.com/docs", "focus": "GPT-4o, o1, o3, function calling, embeddings, streaming, Assistants API"},
        {"name": "OpenAI Cookbook", "url": "https://cookbook.openai.com", "focus": "Practical GPT code examples, RAG, fine-tuning, structured outputs"},
        {"name": "OpenAI Research", "url": "https://openai.com/research", "focus": "GPT-4, o3, reasoning, alignment papers"},
        # Google / DeepMind
        {"name": "Google AI Gemini API Docs", "url": "https://ai.google.dev/gemini-api/docs", "focus": "Gemini 2.0, multimodal, function calling, grounding, token streaming"},
        {"name": "Google DeepMind Research", "url": "https://deepmind.google/research", "focus": "Gemini, AlphaCode, Veo, Imagen, SOTA architectures, papers"},
        {"name": "Google AI Blog", "url": "https://blog.google/technology/google-deepmind", "focus": "Latest DeepMind announcements, model releases, SOTA benchmarks"},
        # DeepSeek
        {"name": "DeepSeek GitHub", "url": "https://github.com/deepseek-ai", "focus": "DeepSeek-V3, DeepSeek-R1, MoE code, reasoning models, model weights"},
        {"name": "DeepSeek API Docs", "url": "https://api-docs.deepseek.com", "focus": "DeepSeek API, chat completions, reasoning endpoint, pricing"},
        {"name": "DeepSeek HuggingFace", "url": "https://huggingface.co/deepseek-ai", "focus": "Model cards, DeepSeek-V3, DeepSeek-R1, quantized variants"},
        # Zhipu AI
        {"name": "Zhipu AI BigModel Platform", "url": "https://open.bigmodel.cn", "focus": "GLM-4, CogVideo, CogView, VisualGLM API, Chinese SOTA models"},
        {"name": "Zhipu AI GitHub", "url": "https://github.com/THUDM", "focus": "ChatGLM, CogVideo, CogView, GLM-4 open source implementations"},
        {"name": "GLM4 API Docs", "url": "https://open.bigmodel.cn/dev/api", "focus": "GLM-4, GLM-4V, embedding, batch API, multimodal Zhipu endpoints"},
        # xAI (Grok)
        {"name": "xAI API Docs", "url": "https://docs.x.ai/api", "focus": "Grok-2, Grok-3, function calling, OpenAI-compatible endpoints, real-time data"},
        {"name": "xAI Blog", "url": "https://x.ai/blog", "focus": "Grok model announcements, Aurora (vision), reasoning capabilities"},
        {"name": "xAI GitHub", "url": "https://github.com/xai-org", "focus": "Grok open weights, Aurora, xAI research code"},
        # Mistral AI
        {"name": "Mistral AI Docs", "url": "https://docs.mistral.ai", "focus": "Mistral Large, Codestral, function calling, embeddings, deployments"},
        {"name": "Mistral AI GitHub", "url": "https://github.com/mistralai", "focus": "Mistral model code, vLLM integrations, fine-tuning recipes"},
        {"name": "Mistral HuggingFace", "url": "https://huggingface.co/mistralai", "focus": "Mistral-7B, Mixtral-8x7B, Codestral model cards and weights"},
        # Meta AI
        {"name": "Meta AI LLaMA Docs", "url": "https://llama.meta.com", "focus": "LLaMA 3, LLaMA 3.1, fine-tuning, deployment guides, Meta AI safety"},
        {"name": "Meta Research", "url": "https://ai.meta.com/research", "focus": "LLaMA papers, open source AI, Meta AI blog, FAIR research"},
        {"name": "Meta LLaMA GitHub", "url": "https://github.com/meta-llama/llama", "focus": "LLaMA 3 code, inference, quantization, integration examples"},
        # Cohere
        {"name": "Cohere Docs", "url": "https://docs.cohere.com", "focus": "Command R+, Embed v3, RAG, rerank, multilingual, tool use"},
        {"name": "Cohere Cookbook", "url": "https://github.com/cohere-ai/cohere-cookbook", "focus": "Practical Cohere code recipes, RAG, classification, semantic search"},
        # General AI Sources
        {"name": "Hugging Face Papers", "url": "https://huggingface.co/papers", "focus": "Latest ML papers, daily AI research digests, model benchmarks"},
        {"name": "Arxiv CS.AI", "url": "https://arxiv.org/list/cs.AI/recent", "focus": "Bleeding-edge AI preprints: reasoning, agents, multimodal, alignment"},
        {"name": "Papers With Code", "url": "https://paperswithcode.com/sota", "focus": "SOTA benchmarks with linked implementations across all AI tasks"},
    ],

    # -------------------------------------------------------------------------
    # LLM PROVIDERS — provider-specific API references and best practices
    # -------------------------------------------------------------------------
    "llm_providers": [
        {"name": "Anthropic API Reference", "url": "https://docs.anthropic.com/en/api", "focus": "Messages API, streaming, models list, token counting, batches, rate limits"},
        {"name": "OpenAI API Reference", "url": "https://platform.openai.com/docs/api-reference", "focus": "Chat, completions, embeddings, images, audio, fine-tuning, structured outputs"},
        {"name": "Gemini API Reference", "url": "https://ai.google.dev/api", "focus": "GenerateContent, streaming, function calling, grounding with Google Search"},
        {"name": "Vertex AI Generative AI", "url": "https://cloud.google.com/vertex-ai/generative-ai/docs", "focus": "Gemini on Vertex, model tuning, RAG Engine, grounding, eval"},
        {"name": "DeepSeek API Reference", "url": "https://api-docs.deepseek.com", "focus": "Chat completions, reasoning model, context caching, OpenAI-compatible"},
        {"name": "xAI API Reference", "url": "https://docs.x.ai/api", "focus": "Grok completions, image understanding, real-time knowledge, pricing"},
        {"name": "Mistral API Reference", "url": "https://docs.mistral.ai/api", "focus": "Chat, function calling, embeddings, batch, FIM for code completion"},
        {"name": "Cohere API Reference", "url": "https://docs.cohere.com/reference", "focus": "Generate, embed, classify, rerank, Command R tool use"},
        {"name": "Together AI Docs", "url": "https://docs.together.ai", "focus": "Open model inference, fine-tuning, embeddings, batch, serverless endpoints"},
        {"name": "Groq Docs", "url": "https://console.groq.com/docs", "focus": "Ultra-fast inference, LLaMA, Mixtral, Gemma, SpecDecoding, low-latency"},
        {"name": "Fireworks AI Docs", "url": "https://docs.fireworks.ai", "focus": "Serverless LLM inference, compound AI, function calling, structured output"},
        {"name": "Replicate Docs", "url": "https://replicate.com/docs", "focus": "Deploy and run ML models in the cloud, streaming, webhooks"},
    ],

    # -------------------------------------------------------------------------
    # MODEL BENCHMARKS — leaderboards, evaluation suites, SOTA comparisons
    # -------------------------------------------------------------------------
    "model_benchmarks": [
        {"name": "LMSYS Chatbot Arena", "url": "https://chat.lmsys.org", "focus": "Live Elo-based LLM ranking, head-to-head model comparisons"},
        {"name": "Open LLM Leaderboard", "url": "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard", "focus": "HuggingFace open model benchmark rankings (MMLU, HellaSwag, TruthfulQA)"},
        {"name": "HELM Benchmark", "url": "https://crfm.stanford.edu/helm", "focus": "Stanford CRFM holistic LLM evaluation across 42 scenarios"},
        {"name": "BIG-bench", "url": "https://github.com/google/BIG-bench", "focus": "Google's 200+ task beyond-imitation-game benchmark"},
        {"name": "Papers With Code SOTA", "url": "https://paperswithcode.com/sota", "focus": "Task-level SOTA tracking with linked model implementations"},
        {"name": "EvalPlus", "url": "https://evalplus.github.io/leaderboard.html", "focus": "Code generation benchmark, HumanEval+, MBPP+"},
        {"name": "SWE-bench", "url": "https://swe-bench.github.io", "focus": "Real-world GitHub issue resolution for coding agents"},
        {"name": "LiveBench", "url": "https://livebench.ai", "focus": "Contamination-free monthly refreshed LLM leaderboard"},
    ],

    # -------------------------------------------------------------------------
    # AGENT FRAMEWORKS — orchestration, tool use, multi-agent patterns
    # -------------------------------------------------------------------------
    "agent_frameworks": [
        {"name": "LangChain Docs", "url": "https://python.langchain.com/docs", "focus": "Chains, agents, RAG, memory, tool use, LangGraph integration"},
        {"name": "LangGraph Docs", "url": "https://langchain-ai.github.io/langgraph", "focus": "Stateful multi-agent graphs, cycles, human-in-the-loop, streaming"},
        {"name": "AutoGen Docs", "url": "https://microsoft.github.io/autogen", "focus": "Microsoft multi-agent framework, group chat, code execution, portfolios"},
        {"name": "CrewAI Docs", "url": "https://docs.crewai.com", "focus": "Role-based multi-agent teams, task delegation, tool integration"},
        {"name": "LlamaIndex Docs", "url": "https://docs.llamaindex.ai", "focus": "RAG, agentic pipelines, data connectors, query engines"},
        {"name": "Smolagents Docs", "url": "https://huggingface.co/docs/smolagents", "focus": "HuggingFace lightweight agents, CodeAgent, tool-calling patterns"},
        {"name": "OpenAI Swarm", "url": "https://github.com/openai/swarm", "focus": "Lightweight multi-agent handoffs and orchestration patterns"},
        {"name": "Semantic Kernel Docs", "url": "https://learn.microsoft.com/en-us/semantic-kernel", "focus": "Microsoft Semantic Kernel, plugins, planners, .NET and Python"},
        {"name": "DSPy Docs", "url": "https://dspy.ai", "focus": "Programmatic LLM prompt optimization, signatures, teleprompters"},
        {"name": "Instructor Docs", "url": "https://python.useinstructor.com", "focus": "Structured LLM outputs with Pydantic validation, retry logic"},
    ],

    # -------------------------------------------------------------------------
    # ML INFRA — training, serving, deployment, optimization
    # -------------------------------------------------------------------------
    "ml_infra": [
        {"name": "vLLM Docs", "url": "https://docs.vllm.ai", "focus": "High-throughput LLM serving, PagedAttention, tensor parallelism, quantization"},
        {"name": "PyTorch Docs", "url": "https://pytorch.org/docs/stable", "focus": "Tensor operations, autograd, CUDA, distributed training, TorchScript"},
        {"name": "JAX Docs", "url": "https://jax.readthedocs.io", "focus": "High-performance ML computation, JIT, grad, vmap, pmap, TPU/GPU"},
        {"name": "HuggingFace Transformers", "url": "https://huggingface.co/docs/transformers", "focus": "Pre-trained models, tokenizers, Trainer, PEFT, fine-tuning"},
        {"name": "HuggingFace PEFT", "url": "https://huggingface.co/docs/peft", "focus": "LoRA, QLoRA, prefix tuning, efficient fine-tuning techniques"},
        {"name": "TGI (Text Generation Inference)", "url": "https://huggingface.co/docs/text-generation-inference", "focus": "HuggingFace serving, continuous batching, streaming, quantization"},
        {"name": "Axolotl GitHub", "url": "https://github.com/axolotl-org/axolotl", "focus": "LLM fine-tuning framework, LoRA, QLoRA, FSDP, DeepSpeed"},
        {"name": "DeepSpeed Docs", "url": "https://deepspeed.ai/docs", "focus": "ZeRO optimizer, 3D parallelism, inference optimization, RLHF"},
        {"name": "Ray Docs", "url": "https://docs.ray.io", "focus": "Distributed computing, Ray Serve, RLlib, data parallel training"},
        {"name": "MLflow Docs", "url": "https://mlflow.org/docs/latest", "focus": "Experiment tracking, model registry, deployment, LLM evaluation"},
    ],

    # -------------------------------------------------------------------------
    # NVIDIA / CUDA — GPU computing, inference acceleration, NIM
    # -------------------------------------------------------------------------
    "nvidia_cuda": [
        {"name": "NVIDIA Developer Docs", "url": "https://developer.nvidia.com/documentation", "focus": "CUDA, TensorRT, NIM, Triton Inference Server, GPU architectures"},
        {"name": "NVIDIA NIM Docs", "url": "https://docs.nvidia.com/nim", "focus": "NVIDIA Inference Microservices, pre-optimized LLM containers, deployment"},
        {"name": "TensorRT-LLM GitHub", "url": "https://github.com/NVIDIA/TensorRT-LLM", "focus": "Optimized LLM inference with TensorRT, quantization, custom ops"},
        {"name": "Triton Inference Server", "url": "https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide", "focus": "Model serving, ensemble models, dynamic batching, metrics"},
        {"name": "NVIDIA NGC Catalog", "url": "https://catalog.ngc.nvidia.com", "focus": "Pre-built GPU containers, CUDA-optimized models, Helm charts"},
        {"name": "CUDA Programming Guide", "url": "https://docs.nvidia.com/cuda/cuda-c-programming-guide", "focus": "CUDA kernels, thread hierarchy, memory model, streams, profiling"},
        {"name": "NVIDIA AI Blog", "url": "https://developer.nvidia.com/blog", "focus": "Latest GPU AI techniques, inference optimization, Blackwell, Hopper"},
        {"name": "cuDNN Docs", "url": "https://docs.nvidia.com/deeplearning/cudnn", "focus": "Deep learning primitives, convolutions, attention operations, GPU acceleration"},
    ],

    # -------------------------------------------------------------------------
    # DEVELOPER ACADEMIES — official learning centers, tutorials, guides
    # -------------------------------------------------------------------------
    "developer_academies": [
        {"name": "Anthropic Academy", "url": "https://www.anthropic.com/learn", "focus": "Official Claude courses, prompt engineering, tool use, responsible AI"},
        {"name": "OpenAI Tutorials", "url": "https://platform.openai.com/docs/tutorials", "focus": "Step-by-step GPT integration tutorials, Assistants, function calling"},
        {"name": "Google AI for Developers", "url": "https://ai.google.dev/learn", "focus": "Gemini tutorials, responsible AI, ML crash course, codelabs"},
        {"name": "DeepLearning.AI Courses", "url": "https://www.deeplearning.ai/courses", "focus": "Andrew Ng AI courses, LLMOps, RAG, agents, fine-tuning with top labs"},
        {"name": "NVIDIA Deep Learning Institute", "url": "https://www.nvidia.com/en-us/training", "focus": "GPU computing, LLM deployment, cuda programming, NIM workshops"},
        {"name": "HuggingFace Courses", "url": "https://huggingface.co/learn", "focus": "NLP course, RL course, audio course, deep RL, open source ML"},
        {"name": "Fast.ai", "url": "https://www.fast.ai", "focus": "Practical deep learning from scratch, top-down approach, modern training"},
        {"name": "Microsoft AI Learning", "url": "https://learn.microsoft.com/en-us/ai", "focus": "Azure OpenAI, Copilot development, responsible AI, Semantic Kernel"},
        {"name": "AWS AI/ML Training", "url": "https://aws.amazon.com/training/learn-about/machine-learning", "focus": "AWS ML certifications, SageMaker, Bedrock, MLOps on AWS"},
        {"name": "Cohere Academy", "url": "https://docs.cohere.com/docs/llmu", "focus": "LLM University, practical NLP, RAG, semantic search fundamentals"},
    ],

    # -------------------------------------------------------------------------
    # CLOUD INFRA — GCP, AWS, Azure deployment and MLOps
    # -------------------------------------------------------------------------
    "cloud_infra": [
        {"name": "Google Cloud Docs", "url": "https://cloud.google.com/docs", "focus": "GCP, Vertex AI, Cloud Run, BigQuery, IAM, Cloud Build, Artifact Registry"},
        {"name": "Vertex AI Generative AI Docs", "url": "https://cloud.google.com/vertex-ai/generative-ai/docs", "focus": "Gemini on Vertex, model tuning, RAG Engine, grounding, eval, endpoints"},
        {"name": "Vertex AI Model Garden", "url": "https://cloud.google.com/vertex-ai/generative-ai/docs/model-garden/explore-models", "focus": "Available Vertex models, endpoints, Anthropic, Meta, DeepSeek on Vertex"},
        {"name": "Cloud Run Docs", "url": "https://cloud.google.com/run/docs", "focus": "Container deployment, auto-scaling, IAM, Domain Mapping, Jobs"},
        {"name": "AWS Bedrock Docs", "url": "https://docs.aws.amazon.com/bedrock", "focus": "Bedrock models, inference, Agents, Knowledge Bases, Claude on AWS"},
        {"name": "Azure OpenAI Service Docs", "url": "https://learn.microsoft.com/en-us/azure/ai-services/openai", "focus": "GPT-4 on Azure, deployments, BYOD, content filtering, private endpoints"},
        {"name": "GitHub Actions Docs", "url": "https://docs.github.com/en/actions", "focus": "CI/CD workflows, runners, artifacts, secrets, matrix builds"},
        {"name": "Docker Hub Docs", "url": "https://docs.docker.com", "focus": "Containerization, Compose, multi-stage builds, GPU containers"},
        {"name": "Kubernetes Docs", "url": "https://kubernetes.io/docs", "focus": "K8s deployments, services, ingress, autoscaling, GPU workloads"},
    ],

    # -------------------------------------------------------------------------
    # SOFTWARE ENGINEERING — core dev tooling, APIs, best practices
    # -------------------------------------------------------------------------
    "software_engineering": [
        {"name": "Python Docs", "url": "https://docs.python.org/3", "focus": "Python stdlib, asyncio, typing, dataclasses, pathlib, subprocess"},
        {"name": "FastAPI Docs", "url": "https://fastapi.tiangolo.com", "focus": "REST APIs, WebSocket, middleware, Pydantic v2, dependency injection"},
        {"name": "Pydantic Docs", "url": "https://docs.pydantic.dev", "focus": "Data validation, schemas, model config, validators, JSON Schema"},
        {"name": "MDN Web Docs", "url": "https://developer.mozilla.org", "focus": "HTML, CSS, JavaScript, WebSockets, Fetch API, Web Workers"},
        {"name": "GitHub Docs", "url": "https://docs.github.com", "focus": "GitHub workflow, PRs, Actions, Codespaces, advanced search"},
        {"name": "Stack Overflow", "url": "https://stackoverflow.com", "focus": "Practical programming Q&A, error resolution, language-specific patterns"},
        {"name": "Ray Docs (Python)", "url": "https://docs.ray.io", "focus": "Async distributed Python, actors, remote functions, serve"},
        {"name": "httpx Docs", "url": "https://www.python-httpx.org", "focus": "Async HTTP client, streaming, retries, timeout, auth, HTTPX in Python"},
    ],

    # -------------------------------------------------------------------------
    # SECURITY — application security, LLM-specific threats
    # -------------------------------------------------------------------------
    "security": [
        {"name": "OWASP Top 10", "url": "https://owasp.org/www-project-top-ten", "focus": "Web application security, XSS, SQLi, injection, CSRF, insecure deserialization"},
        {"name": "OWASP LLM Top 10", "url": "https://owasp.org/www-project-top-10-for-large-language-model-applications", "focus": "LLM-specific risks: prompt injection, insecure output handling, RAG poisoning"},
        {"name": "CWE Database", "url": "https://cwe.mitre.org", "focus": "Software weakness enumeration, root cause mapping"},
        {"name": "NVD", "url": "https://nvd.nist.gov", "focus": "Known CVEs and vulnerability database, CVSS scores"},
        {"name": "Anthropic Responsible AI", "url": "https://www.anthropic.com/safety", "focus": "Claude safety policies, alignment research, constitutional AI"},
        {"name": "AI Safety Papers", "url": "https://arxiv.org/list/cs.AI/recent", "focus": "Alignment, jailbreaks, red-teaming, adversarial robustness research"},
    ],

    # -------------------------------------------------------------------------
    # DATA SCIENCE — datasets, pipelines, embeddings, evaluation
    # -------------------------------------------------------------------------
    "data_science": [
        {"name": "HuggingFace Datasets", "url": "https://huggingface.co/datasets", "focus": "NLP, vision, multimodal datasets, dataset cards, streaming"},
        {"name": "Kaggle Datasets", "url": "https://www.kaggle.com/datasets", "focus": "Public datasets for training, competitions, benchmarking"},
        {"name": "UCI ML Repository", "url": "https://archive.ics.uci.edu/datasets", "focus": "Classic ML datasets for structured data tasks"},
        {"name": "OpenAI Evals", "url": "https://github.com/openai/evals", "focus": "Evaluation framework for LLMs and agents, custom eval registry"},
        {"name": "RAGAS Docs", "url": "https://docs.ragas.io", "focus": "RAG evaluation metrics: faithfulness, answer relevancy, context precision"},
        {"name": "LlamaIndex Evaluation", "url": "https://docs.llamaindex.ai/en/stable/module_guides/evaluating", "focus": "RAG pipeline evaluation, query/response quality, retrieval metrics"},
    ],

    # -------------------------------------------------------------------------
    # GENERAL — broad factual, engineering culture, news
    # -------------------------------------------------------------------------
    "general": [
        {"name": "Wikipedia", "url": "https://en.wikipedia.org", "focus": "General factual knowledge, definitions, history, technical concepts"},
        {"name": "Stack Overflow", "url": "https://stackoverflow.com", "focus": "Practical programming Q&A, error resolution"},
        {"name": "Hacker News", "url": "https://news.ycombinator.com", "focus": "Tech news, engineering culture, cutting-edge projects, AI announcements"},
        {"name": "The Gradient", "url": "https://thegradient.pub", "focus": "In-depth ML research coverage, practitioner perspectives"},
        {"name": "Transformer Circuits", "url": "https://transformer-circuits.pub", "focus": "Mechanistic interpretability research from Anthropic team"},
    ],
}

# ---------------------------------------------------------------------------
# INTERNAL: System-local SOTA sources, always available, no network required.
# ---------------------------------------------------------------------------
INTERNAL_SOTA_SOURCES: List[Dict[str, str]] = [
    {"name": "KnowledgeBank", "location": "knowledge_lessons.json", "focus": "Accumulated operational heuristics from past DAG runs"},
    {"name": "ProjectREADME", "location": "README.md", "focus": "High-level system architecture and capabilities"},
    {"name": "CoreFS Tools", "location": "src/tooloo/tools/core_fs.py", "focus": "Available filesystem and subprocess action schemas"},
    {"name": "LLM Router", "location": "src/tooloo/core/llm.py", "focus": "Available model backends and routing logic"},
    {"name": "MegaDAG", "location": "src/tooloo/core/mega_dag.py", "focus": "Node types, operators, execution pipeline"},
    {"name": "SOTA Sources Registry", "location": "src/tooloo/tools/sota_sources.py", "focus": "This file — canonical domain-partitioned knowledge source registry"},
]

# ---------------------------------------------------------------------------
# DOMAIN ALIASES: Alternative keywords mapped to canonical domain names.
# Used by infer_domain() for broad signal coverage.
# ---------------------------------------------------------------------------
_DOMAIN_KEYWORD_MAP: Dict[str, List[str]] = {
    "ai_research": [
        "claude", "anthropic", "gemini", "deepmind", "gpt", "openai", "llm", "language model",
        "neural", "transformer", "diffusion", "paper", "preprint", "arxiv", "research",
        "foundation model", "multimodal", "vision", "reasoning", "alignment", "rlhf",
    ],
    "llm_providers": [
        "deepseek", "deepseek-r", "deepseek-v", "grok", "xai", "mistral", "codestral", "llama", "meta ai",
        "cohere", "command r", "together", "groq", "fireworks", "replicate",
        "zhipu", "glm", "cogvideo", "bigmodel", "completion", "api key", "endpoint",
        "model provider", "inference api", "chat completions",
        "r1", "r2", "v3", "qwq", "qwen",
    ],
    "model_benchmarks": [
        "benchmark", "leaderboard", "lmsys", "arena", "helm", "mmlu", "hellaswag",
        "truthfulqa", "humaneval", "mbpp", "swe-bench", "evalplus", "livebench",
        "model ranking", "evaluation", "performance comparison",
    ],
    "agent_frameworks": [
        "langchain", "langgraph", "autogen", "crewai", "llamaindex", "smolagents",
        "swarm", "semantic kernel", "dspy", "instructor", "agent framework",
        "multi-agent", "tool use", "orchestration", "agentic",
    ],
    "ml_infra": [
        "vllm", "pytorch", "torch", "jax", "accelerate", "deepspeed", "fsdp",
        "lora", "qlora", "peft", "tgi", "axolotl", "training", "fine-tune", "finetune",
        "quantization", "serving", "inference server", "mlflow", "ray serve",
    ],
    "nvidia_cuda": [
        "cuda", "tensorrt", "nim", "nvidia", "gpu", "dgx", "h100", "a100",
        "blackwell", "hopper", "triton", "ngc", "cudnn", "tensor core",
    ],
    "developer_academies": [
        "learn", "tutorial", "course", "cookbook", "academy", "guide", "lesson",
        "deeplearning.ai", "fast.ai", "training program", "certification",
    ],
    "cloud_infra": [
        "cloud", "gcp", "aws", "azure", "run", "deploy", "container", "k8s",
        "kubernetes", "iam", "bucket", "vertex", "bedrock", "cloud run", "artifact registry",
    ],
    "software_engineering": [
        "python", "fastapi", "pydantic", "api", "websocket", "code", "async",
        "import", "module", "http", "rest", "json", "schema", "library",
    ],
    "security": [
        "security", "xss", "injection", "vuln", "owasp", "cve", "red team",
        "jailbreak", "prompt injection", "adversarial",
    ],
    "data_science": [
        "dataset", "train", "benchmark", "nlp", "vision", "embedding", "retrieval",
        "rag", "evaluation", "ragas", "recall", "precision",
    ],
}


def get_sources_for_domain(domain: str) -> List[Dict[str, str]]:
    """Returns the most relevant SOTA web sources for a given domain keyword."""
    domain = domain.lower().replace("-", "_").replace(" ", "_")

    # Direct match
    if domain in WEB_SOTA_SOURCES:
        return WEB_SOTA_SOURCES[domain]

    # Fuzzy match against source names and focus fields
    matches = []
    seen = set()
    for category, sources in WEB_SOTA_SOURCES.items():
        for s in sources:
            key = s["url"]
            if key not in seen and (domain in s["focus"].lower() or domain in s["name"].lower()):
                matches.append(s)
                seen.add(key)

    return matches if matches else WEB_SOTA_SOURCES["general"]


def infer_domain(goal: str) -> str:
    """
    Heuristically infers the most relevant domain from a goal string.
    Uses keyword scoring: first domain with the most keyword hits wins.
    Falls back to 'general'.
    """
    goal_lower = goal.lower()
    scores: Dict[str, int] = {d: 0 for d in _DOMAIN_KEYWORD_MAP}

    for domain, keywords in _DOMAIN_KEYWORD_MAP.items():
        for kw in keywords:
            if kw in goal_lower:
                scores[domain] += 1

    best_domain = max(scores, key=lambda d: scores[d])
    if scores[best_domain] > 0:
        return best_domain

    return "general"


def get_cross_domain_sources(goal: str, primary_domain: str, max_secondary: int = 2) -> List[Dict[str, str]]:
    """
    Returns sources from the primary domain PLUS up to max_secondary entries from
    a closely related secondary domain for broader JIT coverage.
    """
    goal_lower = goal.lower()
    primary_sources = WEB_SOTA_SOURCES.get(primary_domain, WEB_SOTA_SOURCES["general"])

    # Score all other domains
    scores: Dict[str, int] = {}
    for domain, keywords in _DOMAIN_KEYWORD_MAP.items():
        if domain == primary_domain:
            continue
        scores[domain] = sum(1 for kw in keywords if kw in goal_lower)

    secondary_domain = max(scores, key=lambda d: scores[d]) if scores else "general"
    secondary_sources = WEB_SOTA_SOURCES.get(secondary_domain, [])[:max_secondary]

    # Deduplicate by URL
    seen = {s["url"] for s in primary_sources}
    extras = [s for s in secondary_sources if s["url"] not in seen]

    return primary_sources + extras


def build_source_context(goal: str, lessons: Dict[str, str]) -> str:
    """
    Builds a structured context string for JIT enrichment, combining:
    - Relevant internal lessons from KnowledgeBank
    - Selected trusted web sources for the inferred domain (+ cross-domain)
    """
    domain = infer_domain(goal)
    sources = get_cross_domain_sources(goal, domain, max_secondary=2)

    lesson_block = ""
    if lessons:
        relevant = [(k, v) for k, v in lessons.items() if any(w in goal.lower() for w in k.lower().split("_"))]
        all_lessons = relevant if relevant else list(lessons.items())[:5]
        lesson_block = "\n".join(f"  [{k}]: {v}" for k, v in all_lessons)
    else:
        lesson_block = "  None."

    # Show up to 6 sources in the context block
    source_block = "\n".join(
        f"  [{s['name']}] {s['url']} — {s['focus']}" for s in sources[:6]
    )

    return (
        f"DOMAIN INFERRED: {domain.upper()}\n"
        f"\nINTERNAL KNOWLEDGE BANK LESSONS:\n{lesson_block}\n"
        f"\nTRUSTED SOTA WEB SOURCES FOR THIS DOMAIN:\n{source_block}\n"
        f"\nDIRECTIVE: Use the above sources as the canonical reference ground truth. "
        f"Do not hallucinate APIs, parameters, or capabilities. If you reference a source, cite its name and URL specifically."
    )
