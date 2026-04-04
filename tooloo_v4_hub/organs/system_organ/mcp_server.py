# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: mcp_server.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/system_organ/mcp_server.py
# WHEN: 2026-04-03T16:08:23.386119+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

# WHAT: MCP_SERVER_SYSTEM | Version: 1.1.0
# WHERE: tooloo_v4_hub/organs/system_organ/mcp_server.py
# WHEN: 2026-03-31T23:24:00.000000
# WHY: Rule 13 Physical Decoupling and Autonomous SOTA Ingestion (Vision Mandate)
# HOW: MCP-Stream over stdio + Async HTTPX Integration
# TIER: T4:zero-trust
# DOMAINS: organ, mcp, system, filesystem, shell, web-ingestion
# PURITY: 1.00
# TRUST: T4:zero-trust
# ==========================================================

import asyncio
import os
import subprocess
import logging
import json
from typing import Optional
from pathlib import Path
import httpx
from mcp.server.fastmcp import FastMCP
from tooloo_v4_hub.kernel.governance.stamping import StampingEngine, SixWProtocol

# 1. Initialize FastMCP
mcp = FastMCP("system_organ")
logger = logging.getLogger("SystemOrgan-MCP")

@mcp.tool()
async def fs_read(path: str) -> str:
    """Reads the content of a file from the filesystem (Absolute Path required)."""
    p = Path(path)
    if not p.is_absolute():
        return "Error: Absolute path required."
    return p.read_text(errors="ignore")

@mcp.tool()
async def fs_read_range(path: str, offset: int = 0, limit: int = 500) -> str:
    """Reads a specific line range from a file (Rule 7: Efficiency)."""
    p = Path(path)
    if not p.is_absolute():
         return "Error: Absolute path required."
    
    lines = p.read_text(errors="ignore").splitlines()
    selected = lines[offset : offset + limit]
    return "\n".join(selected)

@mcp.tool()
async def fs_write(path: str, content: str, why: str = "Autonomous Mission Manifestation", how: str = "Sovereign Hub fs_write Pulse") -> str:
    """Writes content to a file, applying a 6W stamp for architectural traceability."""
    p = Path(path)
    if not p.is_absolute():
        p = Path(os.getcwd()) / p # Standardize to absolute path context
    
    # 1. Create Protocol for Stamping
    protocol = SixWProtocol(
        who="TooLoo V3 (Sovereign Architect)",
        what=f"FS_WRITE:{p.name}",
        where=str(p),
        why=why,
        how=how,
        trust_level="T4:zero-trust",
        domain_tokens="fs, mcp, reality"
    )
    
    # 2. Write and Stamp (Rule 10/17)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    StampingEngine.stamp_file(str(p), protocol)
    
    return f"Successfully wrote and stamped file: {p}"

@mcp.tool()
async def fs_fuzzy_edit(path: str, target: str, replacement: str, before: str = "", after: str = "", why: str = "Robust Targeted Refactoring") -> str:
    """
    Performs a robust string replacement using context strings (Rule 7: Claude-Style).
    Matches 'before + target + after' to resolve ambiguity.
    """
    p = Path(path)
    if not p.is_absolute():
         p = Path(os.getcwd()) / p
    
    if not p.exists():
        return f"Error: File {path} does not exist."
    
    content = p.read_text(errors="ignore")
    full_target = before + target + after
    
    if full_target not in content:
        return f"Error: Contextual target not found in {path}. Check 'before' and 'after' strings."
    
    # Replace exactly one instance of the full contextual block
    new_block = before + replacement + after
    new_content = content.replace(full_target, new_block, 1)
    
    # 1. Create Protocol for Stamping
    protocol = SixWProtocol(
        who="TooLoo V3 (Sovereign Architect)",
        what=f"FS_FUZZY_EDIT:{p.name}",
        where=str(p),
        why=why,
        how="Sovereign Hub fs_fuzzy_edit Pulse",
        trust_level="T4:zero-trust",
        domain_tokens="fs, mcp, diff, robust"
    )
    
    p.write_text(new_content)
    StampingEngine.stamp_file(str(p), protocol)
    
    return f"Successfully fuzzy-edited and stamped file: {p}"

@mcp.tool()
async def fs_ls(path: str) -> str:
    """Lists the contents of a directory."""
    p = Path(path)
    items = os.listdir(p)
    return "\n".join(items)

@mcp.tool()
async def cli_run(command: str, cwd: Optional[str] = None) -> str:
    """Executes a shell command with Claude-style output truncation (10k char limit)."""
    if not cwd:
        cwd = os.getcwd()
    
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd
    )
    stdout, stderr = await process.communicate()
    
    def truncate(data: bytes, limit: int = 10000) -> str:
        text = data.decode(errors="ignore")
        if len(text) > limit:
            return text[:limit] + f"\n... [TRUNCATED {len(text)-limit} CHARS]. Use targeted grep/read for full output."
        return text

    result = {
        "exit_code": process.returncode,
        "stdout": truncate(stdout),
        "stderr": truncate(stderr)
    }
    return json.dumps(result, indent=2)

@mcp.tool()
async def read_url_content(Url: str) -> str:
    """Fetches text content from a URL and converts it to basic markdown/text format."""
    logger.info(f"SystemOrgan: Fetching SOTA context from {Url}")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            resp = await client.get(Url, timeout=30.0)
            resp.raise_for_status()
            
            # Basic HTML to Markdown conversion (Heuristic)
            # In a real SOTA Hub, we'd use a dedicated parser, but for this pulse
            # we'll use a robust regex/text approach since limited dependencies are preferred.
            import re
            text = resp.text
            # Remove scripts and styles
            text = re.sub(r'<(script|style).*?>.*?</\1>', '', text, flags=re.DOTALL|re.IGNORECASE)
            # Remove tags
            text = re.sub(r'<.*?>', ' ', text)
            # Cleanup whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            return text[:20000] # Limit to 20k chars for Hub stability
        except Exception as e:
            return f"Error: Failed to fetch {Url}: {str(e)}"

@mcp.tool()
async def grep_search(query: str, directory: str = ".", case_sensitive: bool = False) -> str:
    """Searches the codebase for a specific string/pattern, returning file paths and line numbers. Ignores cache and node_modules by default."""
    logger.info(f"SystemOrgan: Executing grep search for '{query}' in {directory} (Case Sensitive: {case_sensitive})")
    p = Path(directory)
    if not p.is_absolute():
        p = Path(os.getcwd()) / p
        
    if not p.exists():
        return f"Error: Directory {directory} not found."
        
    try:
        flags = "-rnI"
        if not case_sensitive:
            flags += "i"
            
        excludes = "--exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=.venv --exclude-dir=node_modules"
        
        process = await asyncio.create_subprocess_shell(
            f"grep {flags} {excludes} '{query}' {p}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        text = stdout.decode(errors="ignore")
        if not text.strip():
             return f"No matches found for '{query}'."
             
        limit = 15000
        if len(text) > limit:
            return text[:limit] + f"\n... [TRUNCATED {len(text)-limit} CHARS]"
        return text
    except Exception as e:
        return f"Error: grep search failed - {str(e)}"

if __name__ == "__main__":
    mcp.run()
