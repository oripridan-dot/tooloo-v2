# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: MODULE_OPENAI_MCP_SERVER | Version: 1.0.0
# WHERE: tooloo_v3_hub/organs/openai_organ/mcp_server.py
# WHEN: 2026-03-31T23:02:00.000000
# WHY: Rule 13 Federated SOTA Infrastructure (Nerve End of Hub)
# HOW: MCP SDK Stdio Server + OpenAI Enterprise Logic
# TIER: T4:zero-trust
# DOMAINS: mcp, openai, enterprise, sota, academy, federation
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import logging
import sys
from mcp.server.fastmcp import FastMCP
from tooloo_v3_hub.organs.openai_organ.openai_logic import get_openai_logic

# Initialize OpenAI SOTA MCP Server
mcp = FastMCP("openai_organ")
logger = logging.getLogger("OpenAIOrgan")

@mcp.tool()
async def query_enterprise_sota(group: str, query: str = "") -> str:
    """
    On-demand retrieval of Science/Work/Education engrams.
    Groups: science, work, education, stories.
    """
    logic = get_openai_logic()
    result = await logic.query_enterprise_sota(group, query)
    
    if result["status"] == "success":
        engrams = result["engrams"]
        if not engrams:
            return f"No SOTA engrams found for group '{group}' matching '{query}'."
            
        summary = f"--- OPENAI SOTA: {group.upper()} ---\n"
        for i, eng in enumerate(engrams):
            summary += f"\n[{i+1}] SOURCE: {eng.get('url', 'Unknown')}\n"
            summary += f"CONTEXT: {eng.get('content_preview', 'No preview available')[:500]}...\n"
            
        return summary
    else:
        return f"Error: {result.get('message', 'OpenAI Organ Vault Failure')}"

@mcp.tool()
async def get_enterprise_content_list() -> str:
    """Lists available OpenAI Enterprise SOTA domains."""
    logic = get_openai_logic()
    mapping = logic.get_content_list()
    return f"Available OpenAI SOTA Domains:\n" + "\n".join([f"- {k}: {v}" for k, v in mapping.items()])

@mcp.tool()
async def generate_sota_reasoning(prompt: str, model: str = "gpt-5.4", effort: str = "high") -> str:
    """
    Rule 4: SOTA Reasoning Pulse. 
    Triggers GPT-5.4 execution via the bit-perfect Responses API.
    Models: gpt-5.4 (standard), o1-reasoning (deep), gpt-5-mini (latency).
    Effort: none, minimal, low, medium, high, xhigh.
    """
    logic = get_openai_logic()
    res = await logic.generate_sota_reasoning(prompt, model=model, effort=effort)
    
    if res["status"] == "success":
        output = f"--- THINKING PHASE ---\n"
        output += f"REASONING SUMMARY: {res.get('reasoning', 'N/A')}\n\n"
        output += f"--- FINAL RESPONSE ---\n"
        output += res["content"]
        return output
    else:
        return f"Error: {res.get('message', 'OpenAI SOTA Execution Fault')}"

if __name__ == "__main__":
    # Standard MCP server entry point via stdio
    mcp.run()
