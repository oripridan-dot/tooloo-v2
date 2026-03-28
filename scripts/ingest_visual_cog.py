# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining ingest_visual_cog.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.398657
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import asyncio
from engine.psyche_bank import PsycheBank, CogRule

async def ingest():
    bank = PsycheBank()
    
    rules = [
        CogRule(
            id='visual_cog_dual_coding',
            description='Enforce Dual-Coding Theory: present complex logic simultaneously as a structural graph and raw text.',
            pattern='If DAG_complexity > 0.8: trigger visual graph combined with raw syntax',
            enforcement='warn',
            category='narrative_synthesis',
            source='human_curated'
        ),
        CogRule(
            id='visual_cog_gestalt_grouping',
            description='Apply Gestalt Principles: UI must display asynchronous DAG waves physically clustered by their high-level intent.',
            pattern='Group asynchronous execution states into visually distinct synchronous phases',
            enforcement='warn',
            category='narrative_synthesis',
            source='human_curated'
        ),
        CogRule(
            id='visual_cog_pacing_empathy',
            description='Algorithmic empathy: Use low-framerate storyboard updates to build trust during long tasks.',
            pattern='If task_duration > 5s: emit intermediate observing UI frames at 2-3 fps',
            enforcement='warn',
            category='narrative_synthesis',
            source='human_curated'
        )
    ]
    
    for rule in rules:
        success = await bank.capture(rule)
        if success:
            print(f"Successfully ingested rule: {rule.id}")
        else:
            print(f"Failed or skipped rule: {rule.id}")

if __name__ == '__main__':
    asyncio.run(ingest())
