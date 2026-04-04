# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_CHAT_LOGIC_RUNNER.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/organs/sovereign_chat/chat_logic_runner.py
# WHEN: 2026-04-03T10:37:24.472094+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

import asyncio
from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic

if __name__ == '__main__':
    logic = get_chat_logic()
    asyncio.run(logic.run_in_background())
