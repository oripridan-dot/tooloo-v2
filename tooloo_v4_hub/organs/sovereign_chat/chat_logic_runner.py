# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: chat_logic_runner.py | Version: 1.0.0
# WHERE: tooloo_v4_hub/organs/sovereign_chat/chat_logic_runner.py
# WHEN: 2026-04-03T16:08:23.385192+00:00
# WHY: Rule 10: Mandatory 6W Accountability
# HOW: Autonomous Purity Restoration Pulse
# PURITY: 1.00
# ==========================================================

import asyncio
from tooloo_v4_hub.organs.sovereign_chat.chat_logic import get_chat_logic

if __name__ == '__main__':
    logic = get_chat_logic()
    asyncio.run(logic.run_in_background())
