# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining stamping_engine.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.927728
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import os
import re
from pathlib import Path
from typing import Any, Dict, List
from engine.utils import get_6w_template

class StampingEngine:
    """
    Automates 6W Stamping across the TooLoo V2 system.
    Ensures 100% metadata coverage for generated and processed code.
    """
    
    _STAMP_MARKER = "# 6W_STAMP"
    
    @staticmethod
    def is_stamped(content: str) -> bool:
        """Check if the content starts with a 6W stamp."""
        return content.strip().startswith(StampingEngine._STAMP_MARKER)

    @staticmethod
    def extract_metadata(content: str) -> Dict[str, str]:
        """Extract existing 6W metadata from a file's header."""
        metadata = {}
        if not StampingEngine.is_stamped(content):
            return metadata
            
        header = content.split("="*58)[0]
        patterns = {
            "who": r"# WHO:\s*(.*)",
            "what": r"# WHAT:\s*(.*)",
            "where": r"# WHERE:\s*(.*)",
            "when": r"# WHEN:\s*(.*)",
            "why": r"# WHY:\s*(.*)",
            "how": r"# HOW:\s*(.*)",
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, header)
            if match:
                metadata[key] = match.group(1).strip()
        return metadata

    @staticmethod
    def stamp_file(path: str, metadata: Dict[str, Any]) -> bool:
        """Prepend a 6W stamp to a file."""
        file_path = Path(path)
        if not file_path.exists():
            return False
            
        with open(file_path, "r") as f:
            content = f.read()
            
        if StampingEngine.is_stamped(content):
            # Update existing stamp? For now, we only stamp once.
            return False
            
        stamp = get_6w_template(metadata)
        new_content = stamp + "\n" + content
        
        with open(file_path, "w") as f:
            f.write(new_content)
        return True

    @staticmethod
    def audit_directory(dir_path: str) -> Dict[str, List[str]]:
        """Audit a directory for stamped vs unstamped files."""
        report: Dict[str, List[str]] = {"stamped": [], "unstamped": []}
        root = Path(dir_path)
        
        for file in root.rglob("*.py"):
            if ".gemini" in str(file) or "__pycache__" in str(file):
                continue
            with open(file, "r") as f:
                content = f.read()
                if StampingEngine.is_stamped(content):
                    report["stamped"].append(str(file))
                else:
                    report["unstamped"].append(str(file))
        return report

    @staticmethod
    def get_6w_report(dir_path: str) -> List[Dict[str, str]]:
        """Return a list of 6W metadata blocks for all files in a directory."""
        results = []
        root = Path(dir_path)
        for file in root.rglob("*.py"):
            if ".gemini" in str(file) or "__pycache__" in str(file):
                continue
            try:
                with open(file, "r") as f:
                    content = f.read()
                    if StampingEngine.is_stamped(content):
                        meta = StampingEngine.extract_metadata(content)
                        meta["file"] = str(file)
                        results.append(meta)
            except Exception:
                continue
        return results

# --- GREAT STAMPING UTILITY ---
def run_great_stamping(dir_path: str):
    """One-time pass to stamp all foundational files."""
    engine = StampingEngine()
    report = engine.audit_directory(dir_path)
    
    print(f"Auditing {dir_path}...")
    print(f"Stamped: {len(report['stamped'])}")
    print(f"Unstamped: {len(report['unstamped'])}")
    
    for path in report["unstamped"]:
        meta = {
            "who": "TooLoo V2 (Principal Systems Architect)",
            "what": f"Refining {Path(path).name}",
            "where": str(Path(path).parent),
            "why": "System-wide 6W Stamping Hardening",
            "how": "Autonomous Meta-Refinement"
        }
        if engine.stamp_file(path, meta):
            print(f"✓ Stamped: {path}")

if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "engine"
    run_great_stamping(target)
