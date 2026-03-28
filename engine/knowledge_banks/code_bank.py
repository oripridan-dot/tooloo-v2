# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining code_bank.py
# WHERE: engine/knowledge_banks
# WHEN: 2026-03-28T15:54:38.948740
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

"""
engine/knowledge_banks/code_bank.py — SOTA Software Engineering Knowledge Bank.

Covers architecture patterns, testing strategies, security practices,
API design, observability, CI/CD, and performance engineering as of 2026.
"""
from __future__ import annotations

from pathlib import Path

from engine.knowledge_banks.base import KnowledgeBank, KnowledgeEntry

_DEFAULT_PATH = (
    Path(__file__).resolve().parents[3] / "psyche_bank" / "code.cog.json"
)


class CodeBank(KnowledgeBank):
    """Curated software engineering knowledge: patterns to SOTA 2026 practices."""

    def __init__(self, path: Path | None = None, bank_root: Path | None = None) -> None:
        if bank_root is not None:
            path = bank_root / "code.cog.json"
        super().__init__(path or _DEFAULT_PATH)

    @property
    def bank_id(self) -> str:
        return "code"

    @property
    def bank_name(self) -> str:
        return "Code Bank — Architecture to SOTA 2026 Engineering"

    @property
    def domains(self) -> list[str]:
        return [
            "architecture",
            "testing",
            "security",
            "api_design",
            "observability",
            "ci_cd",
            "performance",
            "data_engineering",
            "runtime_safety",
            "developer_experience",
        ]

    def _seed(self) -> None:
        entries = [
            # ── Architecture ───────────────────────────────────────────────────
            KnowledgeEntry(
                id="code_arch_hexagonal",
                title="Hexagonal Architecture (Ports & Adapters)",
                body="Core domain logic has zero dependencies on frameworks, I/O, or databases. All external interaction goes through defined ports (interfaces) with pluggable adapters. Enables full test isolation, postpones infrastructure decisions, facilitates AI-driven refactoring.",
                domain="architecture",
                tags=["architecture", "hexagonal",
                      "ports-adapters", "DDD", "testability"],
                relevance_weight=0.93,
                sota_level="current",
            ),
            KnowledgeEntry(
                id="code_arch_event_driven",
                title="Event-Driven Architecture: Loose Coupling via Events",
                body="Producers emit domain events; consumers react without knowing the source. Use CloudEvents spec for envelope standardisation. Kafka / RedPanda for durable streaming, Redis Streams for lightweight fan-out. Enables audit log by default.",
                domain="architecture",
                tags=["architecture", "events",
                      "kafka", "cloudevents", "async"],
                relevance_weight=0.91,
                sota_level="current",
            ),
            KnowledgeEntry(
                id="code_arch_cqrs_sourcing",
                title="CQRS + Event Sourcing",
                body="Separate read models (projections) from write models (commands). Event sourcing stores every state change as an immutable event — full audit trail and temporal queries. Axon, Marten, and EventStoreDB are production-ready implementations.",
                domain="architecture",
                tags=["architecture", "CQRS",
                      "event-sourcing", "audit", "projection"],
                relevance_weight=0.88,
                sota_level="current",
            ),
            KnowledgeEntry(
                id="code_arch_solid",
                title="SOLID Principles Applied to Modern Code",
                body="SRP: one reason to change per module. OCP: extend via composition, not modification. LSP: subtypes fulfil base contracts. ISP: thin interfaces. DIP: depend on abstractions. Applied rigorously, SOLID produces AI-refactorable, independently testable units.",
                domain="architecture",
                tags=["architecture", "SOLID",
                      "design-principles", "OOP", "coupling"],
                relevance_weight=0.95,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="code_arch_strangler_fig",
                title="Strangler Fig: Incremental Migration Pattern",
                body="Route traffic through a proxy; implement new features in the new system; gradually redirect old routes until the legacy system is 'strangled'. Safe incremental migration with zero big-bang rewrites. Critical for AI-assisted modernisation projects.",
                domain="architecture",
                tags=["architecture", "migration",
                      "strangler-fig", "incremental", "proxy"],
                relevance_weight=0.87,
                sota_level="current",
            ),
            # ── Testing ────────────────────────────────────────────────────────
            KnowledgeEntry(
                id="code_testing_pyramid",
                title="Testing Pyramid: 70/20/10 Distribution",
                body="70% unit tests (fast, isolated), 20% integration tests (real DB/network boundaries), 10% E2E tests (full user flows). Inverting the pyramid creates slow, brittle suites. Property-based testing (Hypothesis, fast-check) augments unit layer.",
                domain="testing",
                tags=["testing", "pyramid", "unit", "integration", "E2E"],
                relevance_weight=0.94,
                sota_level="foundational",
            ),
            KnowledgeEntry(
                id="code_testing_mutation",
                title="Mutation Testing: Validate Test Effectiveness",
                body="Mutation testing (mutmut, Pitest) introduces synthetic bugs to verify tests catch them. 70%+ mutation score is the SOTA target. Coverage without mutation testing is a false safety metric — tests may pass yet miss real defects.",
                domain="testing",
                tags=["testing", "mutation-testing",
                      "coverage", "quality", "mutmut"],
                relevance_weight=0.88,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="code_testing_contract",
                title="Consumer-Driven Contract Tests (Pact)",
                body="Pact contract tests verify API compatibility between producers and consumers without full integration environments. Prevents breaking changes in microservice deploys. Pact broker stores and versions contracts. Mandatory for inter-service APIs.",
                domain="testing",
                tags=["testing", "Pact", "contract-tests",
                      "microservices", "compatibility"],
                relevance_weight=0.87,
                sota_level="current",
            ),
            # ── Security ───────────────────────────────────────────────────────
            KnowledgeEntry(
                id="code_security_supply_chain",
                title="Software Supply Chain Security (SLSA Level 3)",
                body="SLSA Level 3: build on hosted platform, generate signed provenance per build, use Sigstore cosign for artefact signing. Rekor transparency log provides tamper-evident audit. Required for enterprise software procurement in 2026.",
                domain="security",
                tags=["security", "supply-chain",
                      "SLSA", "sigstore", "provenance"],
                relevance_weight=0.93,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="code_security_secrets_management",
                title="Secrets Management: No Hardcoded Credentials",
                body="All secrets loaded at runtime from HashiCorp Vault, AWS Secrets Manager, or GCP Secret Manager. Never in env files committed to VCS. Use `python-dotenv` for local dev only with `.env` in `.gitignore`. Detect via `git-secrets` or `trufflehog` in CI.",
                domain="security",
                tags=["security", "secrets", "vault",
                      "env-vars", "credentials"],
                relevance_weight=0.96,
                sota_level="current",
            ),
            KnowledgeEntry(
                id="code_security_sbom",
                title="SBOM Generation (CycloneDX / SPDX)",
                body="Generate a Software Bill of Materials on every build. CycloneDX is the dominant standard for AI/ML systems; SPDX for compliance-heavy industries. OSV Scanner and Grype check dependencies against vulnerability databases. Required under EU CRA 2026.",
                domain="security",
                tags=["security", "SBOM", "CycloneDX",
                      "vulnerability", "compliance"],
                relevance_weight=0.91,
                sota_level="sota_2026",
            ),
            # ── API Design ─────────────────────────────────────────────────────
            KnowledgeEntry(
                id="code_api_rest_maturity",
                title="REST Maturity Level 3: Hypermedia (HATEOAS)",
                body="Level 3 APIs include hypermedia links in responses, enabling clients to discover available actions without hardcoding URLs. OpenAPI 3.1 + JSON:API or HAL provides standard HATEOAS envelopes. Most LLM tool-use APIs stop at Level 2.",
                domain="api_design",
                tags=["API", "REST", "HATEOAS", "OpenAPI", "hypermedia"],
                relevance_weight=0.86,
                sota_level="current",
            ),
            KnowledgeEntry(
                id="code_api_sse_streaming",
                title="Server-Sent Events for LLM Streaming Responses",
                body="SSE provides unidirectional server→client streaming over a single HTTP connection. Superior to polling for LLM token streams: lower latency, auto-reconnect, works behind HTTP/2 proxies. Format: `data: {json}\\n\\n`. Use `EventSource` on the client.",
                domain="api_design",
                tags=["API", "SSE", "streaming", "LLM", "real-time"],
                relevance_weight=0.93,
                sota_level="sota_2026",
            ),
            # ── Observability ──────────────────────────────────────────────────
            KnowledgeEntry(
                id="code_obs_otel",
                title="OpenTelemetry 2.0: Unified Traces, Metrics, Logs",
                body="OpenTelemetry is the de-facto standard for distributed observability in 2026. Single SDK instruments all three signals. Use OTLP exporter → Grafana LGTM stack (Loki+Grafana+Tempo+Mimir). AI-assisted root-cause analysis via Sentry AI or Grafana ML.",
                domain="observability",
                tags=["observability", "OpenTelemetry",
                      "tracing", "metrics", "Grafana"],
                relevance_weight=0.94,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="code_obs_structured_logging",
                title="Structured Logging: JSON + Correlation IDs",
                body="Emit all logs as JSON with: `timestamp`, `level`, `service`, `trace_id`, `span_id`, `message`, `context`. Correlation IDs propagated via W3C trace context headers enable cross-service log stitching in Loki or Splunk.",
                domain="observability",
                tags=["observability", "logging",
                      "structured", "correlation-id", "JSON"],
                relevance_weight=0.92,
                sota_level="current",
            ),
            # ── CI/CD ──────────────────────────────────────────────────────────
            KnowledgeEntry(
                id="code_cicd_trunk_based",
                title="Trunk-Based Development: Short-Lived Branches",
                body="Trunk-based development (TBD) requires feature branches < 2 days, consistent CI passing on trunk, and feature flags for incomplete features. Produces 4× higher deployment frequency per DORA 2026. Incompatible with long-lived feature branches.",
                domain="ci_cd",
                tags=["CI/CD", "trunk-based",
                      "deployment", "DORA", "feature-flags"],
                relevance_weight=0.92,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="code_cicd_openfeature",
                title="OpenFeature: Standard Feature Flag SDK",
                body="OpenFeature (CNCF) provides a vendor-neutral SDK for feature flags. Backends: LaunchDarkly, Flagsmith, OpenFlagr, or in-process JSON. Decouple deployment from release, run A/B experiments, kill-switch rollouts. Critical for CI/CD at scale.",
                domain="ci_cd",
                tags=["CI/CD", "feature-flags",
                      "OpenFeature", "rollout", "A/B"],
                relevance_weight=0.88,
                sota_level="sota_2026",
            ),
            # ── Performance ────────────────────────────────────────────────────
            KnowledgeEntry(
                id="code_perf_continuous_profiling",
                title="Continuous Profiling: Pyroscope / Grafana Phlare",
                body="Continuous profiling captures CPU/memory flamegraphs in production without overhead using eBPF probes. Pyroscope and Grafana Phlare store CPU profiles over time. Identify regressions before users notice. 2026 SRE baseline practice.",
                domain="performance",
                tags=["performance", "profiling",
                      "flamegraph", "eBPF", "Pyroscope"],
                relevance_weight=0.89,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="code_perf_cache_strategies",
                title="Multi-Layer Caching: Edge → CDN → App → DB",
                body="Cache at the closest layer to the user. Edge (Cloudflare Workers/KV), CDN (stale-while-revalidate), app-level (Redis with read-through), DB query result cache. Each layer reduces latency by 1–3 orders of magnitude. Use cache-aside and write-through patterns.",
                domain="performance",
                tags=["performance", "caching", "Redis", "CDN", "latency"],
                relevance_weight=0.91,
                sota_level="current",
            ),
            # ── Developer Experience ───────────────────────────────────────────
            KnowledgeEntry(
                id="code_dx_devcontainers",
                title="Dev Containers 2.0: Reproducible Environments",
                body="`devcontainer.json` defines the full development environment (runtime, tools, extensions). Dev Containers 2.0 supports multi-container compose setups and lifecycle hooks. Eliminates 'works on my machine'. GitHub Codespaces and local Docker use the same spec.",
                domain="developer_experience",
                tags=["DX", "devcontainers",
                      "reproducibility", "Codespaces", "Docker"],
                relevance_weight=0.90,
                sota_level="sota_2026",
            ),
            KnowledgeEntry(
                id="code_dx_conventional_commits",
                title="Conventional Commits + Semantic Release",
                body="Conventional Commits (`feat:`, `fix:`, `chore:`, `BREAKING CHANGE:`) enable automated CHANGELOG generation, semantic versioning, and release notes via `semantic-release` or `release-please`. Standard practice in 2026 for any actively maintained project.",
                domain="developer_experience",
                tags=["DX", "commits", "semantic-release",
                      "changelog", "versioning"],
                relevance_weight=0.87,
                sota_level="current",
            ),
        ]
        for e in entries:
            self._store.entries.append(e)
