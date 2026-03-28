# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining claudio_simulator.py
# WHERE: scripts
# WHEN: 2026-03-28T15:54:43.397608
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import socket
import json
import time
import random
import os

def run_simulator(socket_path="/tmp/claudio.sock"):
    print(f"[SIMULATOR] Connecting to {socket_path}...")
    
    # Wait for the bridge to create the socket
    for _ in range(10):
        if os.path.exists(socket_path):
            break
        time.sleep(1)
    else:
        print("[ERROR] Socket not found. Is the Studio API running?")
        return

    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(socket_path)
        print("[SIMULATOR] Connected. Sending telemetry...")

        while True:
            # Generate 16D-style telemetry
            telemetry = {
                "snr_db": 150.0 + random.uniform(-1, 1),
                "latency_ms": 10.5 + random.uniform(-0.5, 0.5),
                "spectral_convergence": [random.uniform(-1, 1) for _ in range(20)],
                "dimensions": [random.uniform(0, 1) for _ in range(16)]
            }
            client.sendall(json.dumps(telemetry).encode('utf-8'))
            time.sleep(0.5) # 2Hz updates for the demo
            
    except Exception as e:
        print(f"[SIMULATOR] Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    run_simulator()
