# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: KERNEL_POSE_ENGINE_v3.0.0 — Real-time 3D Telemetry
# WHERE: tooloo_v3_hub/kernel/pose_engine.py
# WHEN: 2026-03-29T12:00:00.000000
# WHY: Persistent Vitality for Federated Entity Manifestations
# HOW: Generative Gait & Physics-based Interpolations
# ==========================================================

import math
import time
import psutil
from typing import Dict, Any, List, Optional

class SovereignPoseEngine:
    """
    The High-Fidelity Pose Engine for TooLoo V3.
    Computes Buddy's skeletal and spatial state at 30Hz for real-time streaming.
    """
    
    def __init__(self):
        # Spatial State
        self.pos = {"x": 0.0, "y": 0.0, "z": 0.0}
        self.rot_y = 0.0
        
        # Skeleton State (Joint Rotations in Radians)
        self.joints = {
            "lLeg": 0.0, "rLeg": 0.0,
            "lArm": 0.0, "rArm": 0.0,
            "head_x": 0.0, "head_y": 0.0,
            "torso_x": 0.0, "torso_y": 0.0
        }
        
        # Behavioral State
        self.target_pos = {"x": 0.0, "z": 0.0}
        self.is_walking = False
        self.walk_phase = 0.0
        self.speed = 0.12 # Sovereign Stroll units per frame
        self.vitality = 1.0 # Global energy multiplier
        self.listening_intensity = 0.0 # Reactive to typing
        self.cpu_load = 0.0
        
        # Interaction State
        self.is_fetching = False
        self.fetch_stage = 0 # 0: approach, 1: reach, 2: recoil
        self.is_sculpting = False
        self.is_speaking = False
        self.sculpt_force = 0.0
        
        # V4 Cognitive Streaming
        self.thought_buffer: List[str] = []
        self.current_thought: str = ""
        self.cognitive_jitter = 0.0 # High-frequency micro-movement during reasoning
        
        # V4 PBR Material Registry
        self.material_registry = {
            "marble": {"roughness": 0.1, "metalness": 0.0, "subsurface": 0.8},
            "basalt": {"roughness": 0.9, "metalness": 0.0, "subsurface": 0.1},
            "steel": {"roughness": 0.2, "metalness": 1.0, "subsurface": 0.0},
            "obsidian": {"roughness": 0.0, "metalness": 0.2, "ior": 1.5},
            "oak": {"roughness": 0.7, "metalness": 0.0, "subsurface": 0.3}
        }

    def update_thought(self, text: str):
        """Streams a partial engram to the thought buffer."""
        self.thought_buffer.append(text)
        self.current_thought = text
        self.cognitive_jitter = 1.0
        logger.info(f"Thought Streamed: {text}")

    def get_pbr_props(self, shard_type: str) -> Dict[str, float]:
        """Returns PBR material properties for the given shard type."""
        return self.material_registry.get(shard_type.lower(), self.material_registry["oak"])

    def trigger_sculpt(self, active: bool):
        """Triggers the 'Reality Sculpting' pose."""
        self.is_sculpting = active
        self.sculpt_force = 1.0 if active else 0.0
        logger.info(f"Reality Sculpting: {'ACTIVE' if active else 'OFF'}")

    def set_target(self, x: float, z: float):
        """Set a 3D destination for Buddy."""
        self.target_pos = {"x": x, "z": z}
        self.is_walking = True

    def update_listening(self, intensity: float):
        """Update reactive listening level (bracing)."""
        self.listening_intensity = intensity

    def trigger_action(self, action: str):
        """Triggers a high-fidelity physical action in Buddy's pose."""
        logger.info(f"Pose Triggered: {action}")
        self.vitality = 2.0 # Energy spike
        
        if "wave" in action:
            self.joints["rArm"] = -2.2 # Waving position
        elif "think" in action or "ponder" in action:
            self.joints["head_x"] = 0.5 # Contemplative lean
            self.joints["torso_x"] = 0.2
        elif "scan" in action:
            self.joints["head_y"] = math.sin(time.time() * 2.0) * 0.8
            self.joints["torso_x"] = 0.3
        elif "come" in action:
            self.set_target(0.0, 8.0)
        elif "far" in action:
            self.set_target(45.0, 45.0)

    def fetch_data(self, target_node_id: str):
        """Triggers a physical 'Fetch' of a system data node."""
        # Heuristic: Map pillar_id to coordinates (assuming 4 pillars)
        # Pillar coordinates: (50, 50), (-50, 50), (50, -50), (-50, -50)
        coords = {
            "p1": (42.0, 42.0), "p2": (-42.0, 42.0),
            "p3": (42.0, -42.0), "p4": (-42.0, -42.0)
        }
        x, z = coords.get(target_node_id, (20.0, 20.0))
        self.set_target(x, z)
        self.is_fetching = True
        self.fetch_stage = 0
        logger.info(f"Sovereign Fetch Initiated: {target_node_id}")

    def compute_next_frame(self, dt: float = 0.033) -> Dict[str, Any]:
        """Calculates the 3D state for the next 30Hz frame."""
        curr_time = time.time()
        
        # 0. System Telemetry (6W STAMP)
        if int(curr_time * 10) % 10 == 0: # Update every second
            self.cpu_load = psutil.cpu_percent() / 100.0
        
        # Vitality Sync: Breathing Pulse (1Hz)
        self.pulse = (math.sin(curr_time * 2.5) * 0.5) + 0.5
        self.vitality = max(1.0, self.vitality - 0.02)
        
        # 1. Macro-Navigation (Drift toward target)
        if self.is_walking:
            dx = self.target_pos["x"] - self.pos["x"]
            dz = self.target_pos["z"] - self.pos["z"]
            dist = math.sqrt(dx*dx + dz*dz)
            
            if dist > 1.2:
                # Normal Walk logic...
                norm_x, norm_z = dx/dist, dz/dist
                self.pos["x"] += norm_x * self.speed * dt * 30
                self.pos["z"] += norm_z * self.speed * dt * 30
                target_ang = math.atan2(dx, dz)
                self.rot_y = self._lerp_angle(self.rot_y, target_ang, 0.1)
                self.walk_phase += 10.0 * dt
                swing = math.sin(self.walk_phase) * 0.8
                self.joints["lLeg"] = swing
                self.joints["rLeg"] = -swing
                self.joints["lArm"] = -swing * 0.6
                self.joints["rArm"] = THREE_Math_Lerp(self.joints["rArm"], swing * 0.6, 0.2)
                self.joints["torso_x"] = 0.2
            else:
                self.is_walking = False
                self._stop_walking()
                if self.is_fetching: self.fetch_stage = 1 # Start reach
        
        elif self.is_fetching:
            # Stage 1: REACH
            if self.fetch_stage == 1:
                self.joints["rArm"] = THREE_Math_Lerp(self.joints["rArm"], -2.5, 0.15)
                self.joints["torso_x"] = THREE_Math_Lerp(self.joints["torso_x"], 0.4, 0.1)
                if abs(self.joints["rArm"] + 2.5) < 0.1: self.fetch_stage = 2
            # Stage 2: RECOIL
            elif self.fetch_stage == 2:
                self.joints["rArm"] = THREE_Math_Lerp(self.joints["rArm"], 0.0, 0.1)
                self.joints["torso_x"] = THREE_Math_Lerp(self.joints["torso_x"], -0.1, 0.1)
                if abs(self.joints["rArm"]) < 0.1:
                    self.is_fetching = False
                    self.fetch_stage = 0
                    logger.info("Sovereign Ingestion Complete.")
        
        elif self.is_sculpting:
            # Reality Sculpting: Arms raised, complex shaping pattern
            self.joints["lArm"] = -1.5 + math.sin(curr_time * 5.0) * 0.5
            self.joints["rArm"] = -1.5 + math.cos(curr_time * 5.0) * 0.5
            self.joints["torso_x"] = 0.3 + math.sin(curr_time * 2.0) * 0.1
            self.joints["head_x"] = 0.4
            # Energy burst effect info
            self.vitality = 2.5 
            
        else:
            # Idle Breathing logic...
            self.joints["torso_x"] = 0.1 + math.sin(curr_time * 1.5) * 0.05
            self.joints["lArm"] = math.sin(curr_time * 2.0) * 0.1
            self.joints["rArm"] = THREE_Math_Lerp(self.joints["rArm"], -math.sin(curr_time * 2.0) * 0.1, 0.1)
            self._stop_walking()

        # 2. Vitality: Listening / Bracing / Speaking
        self.joints["torso_x"] += self.listening_intensity * 0.4
        self.pos["y"] = - (self.listening_intensity * 1.0) # Squatting

        # Speaking Jitter
        if self.is_speaking:
            self.joints["head_y"] += math.sin(curr_time * 50.0) * 0.03
            self.joints["torso_x"] += math.sin(curr_time * 40.0) * 0.01

        # 3. Micro-Jitter (Standard + Cognitive)
        jitter_freq = 20.0 + (self.cognitive_jitter * 30.0)
        jitter_amp = 0.01 + (self.cognitive_jitter * 0.05)
        self.joints["head_y"] += math.sin(curr_time * jitter_freq) * jitter_amp
        
        # Decay cognitive jitter
        self.cognitive_jitter = max(0.0, self.cognitive_jitter - 0.05)

        # 4. Ethereal Spark (Randomized melodic trigger)
        spark = 1.0 if (math.sin(curr_time * 30.0) > 0.98 and self.is_fetching) else 0.0

        return {
            "type": "pose_update",
            "pos": self.pos,
            "rot_y": self.rot_y,
            "joints": self.joints,
            "vitality": self.vitality,
            "pulse": self.pulse,
            "spark": spark,
            "sculpting": self.is_sculpting,
            "speaking": self.is_speaking,
            "sculpt_force": self.sculpt_force,
            "load": self.cpu_load,
            "t": curr_time
        }

    def _stop_walking(self):
        """Gracefully settle from walking state."""
        self.joints["lLeg"] *= 0.5
        self.joints["rLeg"] *= 0.5
        
    def _lerp_angle(self, start, end, t):
        """Smoothly interpolate angles (radians)."""
        diff = (end - start + math.pi) % (math.pi * 2) - math.pi
        return start + diff * t

def THREE_Math_Lerp(a, b, t):
    return a + (b - a) * t

import logging
logger = logging.getLogger(__name__)

# --- Global Engine Instance ---
_pose_engine: Optional[SovereignPoseEngine] = None

def get_pose_engine() -> SovereignPoseEngine:
    global _pose_engine
    if _pose_engine is None:
        _pose_engine = SovereignPoseEngine()
    return _pose_engine
