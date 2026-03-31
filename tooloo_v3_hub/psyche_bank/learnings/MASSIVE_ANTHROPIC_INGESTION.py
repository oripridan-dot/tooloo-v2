import asyncio
import logging
import json
import os
import sys
import re
from pathlib import Path
import requests

# Add workspace to sys.path
workspace_root = Path("/Users/oripridan/ANTIGRAVITY/tooloo-v2")
sys.path.append(str(workspace_root))

from tooloo_v3_hub.organs.memory_organ.memory_logic import get_memory_logic
from tooloo_v3_hub.kernel.governance.stamping import SixWProtocol

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger("AnthropicIngestor")

# SOTA URLs - CORRECTED 100% MANIFEST
URLS = [
    # --- Anthropic Platform ---
    "https://platform.claude.com/docs/en/home",
    "https://platform.claude.com/docs/en/intro",
    "https://platform.claude.com/docs/en/api/overview",
    "https://platform.claude.com/docs/en/api/beta-headers",
    "https://platform.claude.com/docs/en/build-with-claude/administration-api",
    "https://platform.claude.com/docs/en/build-with-claude/data-residency",
    "https://platform.claude.com/docs/en/build-with-claude/workspaces",
    "https://platform.claude.com/docs/en/build-with-claude/usage-cost-api",
    "https://platform.claude.com/docs/en/build-with-claude/claude-code-analytics-api",
    "https://platform.claude.com/docs/en/test-and-evaluate/eval-tool",
    "https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency",
    "https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations",
    "https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/increase-consistency",
    "https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks",
    "https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/handle-streaming-refusals",
    "https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-prompt-leak",
    # Agent SDK & Advanced Tools
    "https://platform.claude.com/docs/en/agent-sdk/file-checkpointing",
    "https://platform.claude.com/docs/en/agent-sdk/structured-outputs",
    "https://platform.claude.com/docs/en/agent-sdk/hosting",
    "https://platform.claude.com/docs/en/agent-sdk/secure-deployment",
    "https://platform.claude.com/docs/en/agent-sdk/modifying-system-prompts",
    "https://platform.claude.com/docs/en/agent-sdk/mcp",
    "https://platform.claude.com/docs/en/agent-sdk/custom-tools",
    "https://platform.claude.com/docs/en/agent-sdk/subagents",
    "https://platform.claude.com/docs/en/agent-sdk/slash-commands",
    "https://platform.claude.com/docs/en/agent-sdk/skills",
    "https://platform.claude.com/docs/en/agent-sdk/cost-tracking",
    "https://platform.claude.com/docs/en/agent-sdk/todo-tracking",
    "https://platform.claude.com/docs/en/agent-sdk/plugins",
    "https://platform.claude.com/docs/en/agents-and-tools/mcp-connector",
    "https://platform.claude.com/docs/en/agents-and-tools/remote-mcp-servers",
    "https://platform.claude.com/docs/en/agents-and-tools/computer-use",
    "https://platform.claude.com/docs/en/agents-and-tools/browser-use",
    "https://platform.claude.com/docs/en/agents-and-tools/shell-use",
    "https://platform.claude.com/docs/en/agents-and-tools/files-use",
    "https://platform.claude.com/docs/en/agents-and-tools/multi-agent-orchestrator",
    "https://platform.claude.com/docs/en/agents-and-tools/tool-choice",
    "https://platform.claude.com/docs/en/agents-and-tools/vision",
    "https://platform.claude.com/docs/en/agents-and-tools/prompt-caching",
    "https://platform.claude.com/docs/en/agents-and-tools/advanced-reasoning",
    
    # --- MCP (Corrected Structure) ---
    "https://modelcontextprotocol.io/docs/getting-started/intro",
    "https://modelcontextprotocol.io/docs/getting-started/quickstart",
    "https://modelcontextprotocol.io/docs/getting-started/core-concepts",
    "https://modelcontextprotocol.io/docs/learn/architecture",
    "https://modelcontextprotocol.io/docs/learn/server-concepts",
    "https://modelcontextprotocol.io/docs/learn/client-concepts",
    "https://modelcontextprotocol.io/docs/develop/build-server",
    "https://modelcontextprotocol.io/docs/develop/build-client",
    "https://modelcontextprotocol.io/docs/develop/connect-local-servers",
    "https://modelcontextprotocol.io/docs/develop/connect-remote-servers",
    "https://modelcontextprotocol.io/docs/develop/build-with-agent-skills",
    "https://modelcontextprotocol.io/docs/sdk",
    "https://modelcontextprotocol.io/docs/tutorials/security/authorization",
    "https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices",
    "https://modelcontextprotocol.io/docs/tools/inspector",
    "https://modelcontextprotocol.io/docs/tools/debugging",
    "https://modelcontextprotocol.io/specification/2025-11-25",
    "https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle",
    "https://modelcontextprotocol.io/specification/2025-11-25/basic/transports",
    "https://modelcontextprotocol.io/specification/2025-11-25/client/roots",
    "https://modelcontextprotocol.io/specification/2025-11-25/server",
    "https://modelcontextprotocol.io/clients",
    "https://modelcontextprotocol.io/examples",
    "https://modelcontextprotocol.io/registry/about",
    "https://modelcontextprotocol.io/registry/quickstart",
    "https://modelcontextprotocol.io/registry/authentication",
    "https://modelcontextprotocol.io/registry/package-types",
    "https://modelcontextprotocol.io/registry/github-actions",
    "https://modelcontextprotocol.io/registry/terms-of-service",
    "https://modelcontextprotocol.io/registry/faq",
    "https://modelcontextprotocol.io/registry/registry-aggregators",
    "https://modelcontextprotocol.io/registry/remote-servers"
]

def clean_html(html):
    text = re.sub(r'<script.*?</script>', '', html, flags=re.DOTALL)
    text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<.*?>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def ingest_url_direct(url: str, semaphore: asyncio.Semaphore, memory):
    async with semaphore:
        # Check if already vectorized to save bandwidth
        engram_id = f"sota_anthropic_{abs(hash(url))}"
        # (Heuristic: we'll overwrite to ensure latest SOTA is in memory)
        logger.info(f"Ingesting: {url}")
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to fetch {url}: {response.status_code}")
                return False
                
            text_content = clean_html(response.text)
            
            data = {
                "type": "documentation",
                "source": "anthropic_sota",
                "url": url,
                "text": text_content[:10000],
                "metadata": {"title": url.split("/")[-1], "full_url": url}
            }
            
            protocol = SixWProtocol(
                who="Autonomous-SOTA-Ingestor-V3",
                what="MASSIVE_DOCUMENTATION_INGESTION_FINAL",
                where=url,
                why="Vectorize 100% Corrected Anthropic/MCP Platform Knowledge",
                how="High-Concurrency Async Retrieval + Rescue Logic",
                trust_level="T3:arch-purity"
            )
            data["stamp"] = protocol.model_dump()
            
            await memory.store(engram_id, data)
            logger.info(f"Successfully vectorized: {url}")
            return True
        except Exception as e:
            logger.error(f"Error during ingestion of {url}: {e}")
            return False

async def run_massive_ingestion():
    memory = await get_memory_logic()
    semaphore = asyncio.Semaphore(10) # Max concurrency for rescue completion
    
    logger.info(f"--- STARTING SOVEREIGN INGESTION (RESCUE MISSION: 100% COMPLETION) ---")
    logger.info(f"TARGET PANORAMA: {len(URLS)} refined SOTA documentation endpoints.")
    
    tasks = [ingest_url_direct(url, semaphore, memory) for url in URLS]
    results = await asyncio.gather(*tasks)
    
    success = sum(1 for r in results if r)
    logger.info(f"--- INGESTION COMPLETE ---")
    logger.info(f"Final Count: {success}/{len(URLS)} documents vectorized.")
    
    await memory.soul_sync()
    logger.info("Engrams persisted to psyche_bank (RESCUE MISSION SUCCESS).")

if __name__ == "__main__":
    asyncio.run(run_massive_ingestion())
