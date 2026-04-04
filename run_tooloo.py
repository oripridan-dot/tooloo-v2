# 6W_STAMP
# WHO: TooLoo V4 (Sovereign Architect)
# WHAT: RUN_TOOLOO.PY | Version: 1.0.0
# WHERE: tooloo_v4_hub/run_tooloo.py
# WHY: Rule 13 - Orchestrated Manifestation
# HOW: Async Parallel Service Pulse
# ==========================================================

import asyncio
import os
import subprocess
import sys

async def run_service(name, cmd, port):
    print(f"[LAUNCH] Starting {name} on port {port}...")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{env.get('PYTHONPATH', '')}:."
    
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env
    )
    
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        print(f"[{name}] {line.decode().strip()}")

async def main():
    # 1. Start Hub API (Port 8080)
    
    hub_cmd = "python3 -m tooloo_v4_hub.kernel.hub_api"
    
    await asyncio.gather(
        run_service("HUB_API", hub_cmd, 8080)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Sovereign Services Severed.")
