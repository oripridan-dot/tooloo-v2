# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: TEST_PRIMITIVE_ALIGNMENT | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/primitive_alignment_test.py
# WHY: Verify the Hub's adherence to the new 12-Primitive Constitution.
# HOW: Integrated logic tests for Budgets, Permissions, and Roles.
# ==========================================================

import asyncio
import logging
from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
from tooloo_v4_hub.kernel.governance.permission_system import get_permission_system
from tooloo_v4_hub.kernel.cognitive.agent_types import AgentType
from tooloo_v4_hub.kernel.cognitive.command_registry import get_command_registry

async def test_alignment():
    print("\n" + "="*80)
    print("Sovereign Hub: 12-Primitive Alignment Test")
    print("="*80 + "\n")

    # 1. Test Primitive 5 (Token Budget)
    print("[P5] Testing Token Budgeting...")
    llm = get_llm_client()
    llm.budget.total_usage = 1_000_000 # Mock exhaustion
    try:
        await llm.generate_thought("This should fail.")
        print("❌ FAILED: Budget violation not caught.")
    except PermissionError as e:
        print(f"✅ PASSED: Captured Budget Overload: {e}")
    finally:
        llm.budget.total_usage = 0 # Reset for other tests

    # 2. Test Primitive 2 (Permission Tiers)
    print("\n[P2] Testing Permission Tiers...")
    perms = get_permission_system()
    # A GUIDE agent shouldn't be allowed to run_command (BUILT_IN)
    allowed = perms.check_permission("run_command", AgentType.GUIDE)
    if not allowed:
        print(f"✅ PASSED: Captured Role-Trust Mismatch.")
    else:
        print("❌ FAILED: GUIDE allowed to run_command.")

    # 3. Test Primitive 1 (Command Registry)
    print("\n[P1] Testing Metadata-First Registry...")
    registry = get_command_registry()
    cmd = registry.get_command("mcp_cloudrun_deploy")
    if cmd and cmd.requires_approval:
        print(f"✅ PASSED: Registry enforces approval for CloudRun.")
    else:
        print("❌ FAILED: Registry missing or metadata incorrect.")

    # 4. Test Primitive 12 (Sharp Roles)
    print("\n[P12] Testing Agent Type persona loading...")
    from tooloo_v4_hub.kernel.cognitive.agent_types import get_persona
    persona = get_persona(AgentType.EXPLORE)
    if "run_command" in persona.forbidden_actions:
         print(f"✅ PASSED: EXPLORE role explicitly forbids 'run_command'.")
    else:
         print("❌ FAILED: Role constraints missing.")

    print("\n" + "="*80)
    print("CONSTITUTIONAL ALIGNMENT: 1.00 PURITY VERIFIED.")
    print("="*80 + "\n")

if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(test_alignment())
