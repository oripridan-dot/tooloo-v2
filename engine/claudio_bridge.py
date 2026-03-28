# 6W_STAMP
# WHO: TooLoo V2 (Principal Systems Architect)
# WHAT: Refining claudio_bridge.py
# WHERE: engine
# WHEN: 2026-03-28T15:54:38.927305
# WHY: System-wide 6W Stamping Hardening
# HOW: Autonomous Meta-Refinement
# ==========================================================

import os
import socket
import threading
import json
import time

class ClaudioBridge:
    """
    Unix Domain Socket (UDS) bridge for Claudio C++ engine integration.
    Listens for high-frequency telemetry and broadcasts it to the Studio API.
    """
    def __init__(self, socket_path="/tmp/claudio.sock"):
        self.socket_path = socket_path
        self.running = False
        self.thread = None
        self._last_telemetry = {}
        self._lock = threading.Lock()
        self._subscribers = []

    def start(self):
        if self.running:
            return
        
        # Cleanup stale socket
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)
            
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        print(f"[ClaudioBridge] Started listening on {self.socket_path}")

    def stop(self):
        self.running = False
        if self.thread:
            # We can't easily interrupt accept(), so we rely on daemon thread or a sentinel connection
            pass

    def subscribe(self, callback):
        with self._lock:
            self._subscribers.append(callback)

    def get_latest(self):
        with self._lock:
            return self._last_telemetry

    def _listen_loop(self):
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.socket_path)
        server.listen(1)
        server.settimeout(1.0) # Allow checking self.running
        
        while self.running:
            try:
                conn, _ = server.accept()
                with conn:
                    while self.running:
                        data = conn.recv(4096)
                        if not data:
                            break
                        try:
                            # Assume JSON packets for telemetry
                            # In production, this would be a binary C-struct for speed
                            payload = json.loads(data.decode('utf-8'))
                            with self._lock:
                                self._last_telemetry = payload
                                for sub in self._subscribers:
                                    sub(payload)
                        except Exception as e:
                            print(f"[ClaudioBridge] Parse error: {e}")
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[ClaudioBridge] Listen error: {e}")
                time.sleep(1)

_instance = None
def get_claudio_bridge():
    global _instance
    if _instance is None:
        _instance = ClaudioBridge()
    return _instance
