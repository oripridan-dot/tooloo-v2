import os
import re
from pathlib import Path

def align_hub():
    root = Path("tooloo_v3_hub")
    
    replacements = {
        # 1. Sync-Object Removal (Fixing 'await' and other accidental I/O)
        r"get_mcp_nexus": "get_mcp_nexus",
        r"get_mcp_nexus": "get_mcp_nexus",
        r"get_living_map": "get_living_map",
        r"get_audit_agent": "get_audit_agent",
        r"get_audit_agent": "get_audit_agent",
        r"get_orchestrator": "get_orchestrator",
        r"get_ouroboros": "get_ouroboros"
    }
    
    for file in root.rglob("*.py"):
        content = file.read_text()
        original = content
        
        for pattern, replacement in replacements.items():
            content = re.sub(pattern, replacement, content)
            
        if content != original:
            file.write_text(content)
            print(f"✅ Re-Aligned (Sync-Fix) -> {file}")

if __name__ == "__main__":
    align_hub()
