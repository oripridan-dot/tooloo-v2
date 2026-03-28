# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining utils.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.927852
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

from datetime import datetime
from typing import Any, Dict

def get_6w_template(metadata: Dict[str, Any]) -> str:
    """
    Returns a standardized 6W Stamping block (Who, What, Where, When, Why, hoW).
    """
    now = datetime.now().isoformat()
    who = metadata.get("who", "TooLoo V2 (Principal Systems Architect)")
    what = metadata.get("what", "System Architecture Refinement")
    where = metadata.get("where", "engine/core")
    when = metadata.get("when", now)
    why = metadata.get("why", "Inward Power & SOTA Hardening")
    how = metadata.get("how", "Autonomous 4D Cognitive Routing")

    return (
        f"# 6W_STAMP\n"
        f"# WHO: {who}\n"
        f"# WHAT: {what}\n"
        f"# WHERE: {where}\n"
        f"# WHEN: {when}\n"
        f"# WHY: {why}\n"
        f"# HOW: {how}\n"
        f"# {'='*58}\n"
    )

def extract_json(text: str) -> dict[str, Any] | None:
    """
    Robust JSON extraction from LLM responses.
    Handles fenced code blocks, mixed text, and common formatting artifacts.
    """
    if not text:
        return None

    # Step 1: Look for fenced JSON blocks (```json ... ```)
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        try:
            return json.loads(fenced_match.group(1))
        except json.JSONDecodeError:
            pass

    # Step 2: Look for the largest balanced { ... } block
    # Simple regex for first-level balanced braces
    braced_match = re.search(r"\{.*\}", text, re.DOTALL)
    if braced_match:
        try:
            return json.loads(braced_match.group(0))
        except json.JSONDecodeError:
            # Try once more by stripping potential garbage outside the braces
            try:
                content = braced_match.group(0).strip()
                return json.loads(content)
            except json.JSONDecodeError:
                pass

    return None

def sanitize_shell_output(text: str) -> str:
    """
    Cleans up shell output by removing control characters and excessive whitespace.
    """
    if not text:
        return ""
    # Remove ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean = ansi_escape.sub('', text)
    return clean.strip()
