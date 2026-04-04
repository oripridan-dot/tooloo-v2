# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_NARRATIVE_LEDGER.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/kernel/cognitive/narrative_ledger.py
# WHEN: 2026-04-04T00:41:42.484571+00:00
# WHY: Heal STAMP_PURITY_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("NarrativeLedger")

@dataclass
class Milestone:
    id: str
    title: str
    description: str
    timestamp: float = field(default_factory=time.time)
    purity_impact: float = 0.0
    vitality_impact: float = 0.0
    tags: List[str] = field(default_factory=list)

class NarrativeLedger:
    """
    Tracks the 'Story of the Build'.
    Provides Buddy with a continuous sense of project progress.
    """
    
    def __init__(self, ledger_file: str = "tooloo_v4_hub/psyche_bank/narrative_ledger.json"):
        self.path = Path(ledger_file)
        self.milestones: List[Milestone] = []
        self._load_ledger()

    def _load_ledger(self):
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text())
                for m in data.get("milestones", []):
                    self.milestones.append(Milestone(**m))
                logger.info(f"Narrative Ledger Loaded: {len(self.milestones)} Milestones recorded.")
            except Exception as e:
                logger.error(f"Failed to load Narrative Ledger: {e}")

    def _save_ledger(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "meta": {
                "last_update": time.time(),
                "total_milestones": len(self.milestones),
                "current_purity_delta": sum(m.purity_impact for m in self.milestones)
            },
            "milestones": [m.__dict__ for m in self.milestones]
        }
        self.path.write_text(json.dumps(data, indent=2))

    def record_milestone(self, id: str, title: str, description: str, purity: float = 0.0, vitality: float = 0.0, tags: List[str] = []):
        """Records a new project milestone and persists the narrative."""
        # Avoid duplicates
        if any(m.id == id for m in self.milestones):
            return
            
        m = Milestone(id=id, title=title, description=description, purity_impact=purity, vitality_impact=vitality, tags=tags)
        self.milestones.append(m)
        self._save_ledger()
        logger.info(f"PROJECT_MILESTONE: {title} (Recorded)")

    def get_narrative_summary(self) -> str:
        """Generates a concise story of the project build for Buddy's context."""
        if not self.milestones:
            return "Project Genesis: Hub in Initial State."
            
        summary = "Project Narrative Summary:\n"
        # Last 5 milestones
        recent = sorted(self.milestones, key=lambda x: x.timestamp, reverse=True)[:5]
        for m in reversed(recent):
            summary += f"- {m.title}: {m.description}\n"
        return summary

_ledger: Optional[NarrativeLedger] = None

def get_narrative_ledger() -> NarrativeLedger:
    global _ledger
    if _ledger is None:
        _ledger = NarrativeLedger()
    return _ledger