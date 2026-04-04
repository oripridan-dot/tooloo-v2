# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: TEST_NORTH_STAR | Version: 1.0.0
# WHERE: tests/test_north_star.py
# WHEN: 2026-04-03T14:45:00.000000
# WHY: Rule 16: Evaluation Delta (Verification)
# HOW: Pytest / Unit Logic
# ==========================================================

import os
import json
from tooloo_v4_hub.kernel.cognitive.north_star import SovereignNorthStar, NorthStarState

TEST_STORAGE = "tooloo_v4_hub/psyche_bank/test_north_star.json"

def clean_storage():
    if os.path.exists(TEST_STORAGE):
        os.remove(TEST_STORAGE)

def test_north_star_persistence():
    """Verifies that the North Star can save and load state correctly."""
    clean_storage()
    navigator = SovereignNorthStar(storage_path=TEST_STORAGE)
    
    # Update state
    navigator.update(
        macro_goal="Capture the Flag",
        current_focus="Infiltration",
        micro_goals=["Bypass firewall", "Dump database"],
        completed_milestones=["Reconnaissance"]
    )
    
    # Create new instance and load
    new_navigator = SovereignNorthStar(storage_path=TEST_STORAGE)
    assert new_navigator.state.macro_goal == "Capture the Flag"
    assert new_navigator.state.current_focus == "Infiltration"
    assert "Bypass firewall" in new_navigator.state.micro_goals
    assert "Reconnaissance" in new_navigator.state.completed_milestones
    clean_storage()

def test_north_star_defaults():
    """Verifies default values for a new North Star."""
    tmp_path = "tmp_ns.json"
    if os.path.exists(tmp_path): os.remove(tmp_path)
    navigator = SovereignNorthStar(storage_path=tmp_path)
    try:
        assert navigator.state.macro_goal == "Initialize System Sovereignty"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

if __name__ == "__main__":
    # Manual run support
    print("Running North Star Integrity Audit...")
    try:
        test_north_star_persistence()
        print("Persistence: PURE (1.00)")
        test_north_star_defaults()
        print("Defaults: PURE (1.00)")
        print("Audit COMPLETE.")
    except Exception as e:
        print(f"Audit FAILED: {e}")
        exit(1)
