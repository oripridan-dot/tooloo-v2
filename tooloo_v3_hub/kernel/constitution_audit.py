# 6W_STAMP
# WHO: TooLoo V3 (Sovereign Architect)
# WHAT: CONSTITUTION_AUDIT.PY | Version: 1.0.0 | Version: 1.0.0
# WHERE: tooloo_v3_hub/kernel/constitution_audit.py
# WHEN: 2026-03-31T14:26:13.344528+00:00
# WHY: new - no history
# HOW: Safe Mass Saturation Pulse
# TRUST: T3:arch-purity
# TIER: T3:architectural-purity
# DOMAINS: kernel, unmapped, initial-v3
# PURITY: 1.00
# ==========================================================

import os
import json
import ast
from pathlib import Path

class ConstitutionAuditor:
    def __init__(self, root_dir: str):
        self.root = Path(root_dir)
        self.report = {"compliance_score": 0.0, "rules": {}}

    def scan_ecosystem(self):
        print("Initiating Sovereign Introspection against the 14-Rule Constitution...")
        
        # Rule 1: (C+I)/*ENV Formula
        r1_passed = self._check_keyword_in_file("tooloo_v3_hub/kernel/cognitive/value_evaluator.py", "(C+I)/*ENV")
        self._log_rule("Rule 1: (C+I)/*ENV Formula", r1_passed, "Value Evaluator does not natively score using (C+I)/*ENV.")

        # Rule 2: Async Parallel DAGs (Exists in orchestrator.py)
        r2_passed = self._check_keyword_in_file("tooloo_v3_hub/kernel/orchestrator.py", "asyncio.Semaphore")
        self._log_rule("Rule 2: Async Parallel DAGs", r2_passed, "")

        # Rule 3: Native RAG
        r3_passed = self._check_keyword_in_file("tooloo_v3_hub/organs/memory_organ/memory_logic.py", "embedding") or \
                    self._check_keyword_in_file("tooloo_v3_hub/organs/memory_organ/memory_logic.py", "vector")
        self._log_rule("Rule 3: Native RAG", r3_passed, "Memory Organ does not implement true mathematical semantic embeddings/RAG.")

        # Rule 4: Mandatory SOTA JIT Injection
        r4_passed = self._check_mandatory_jit()
        self._log_rule("Rule 4: Mandatory SOTA JIT", r4_passed, "JIT SOTA is conditionally used for rescue, but not uniformly enforced pre-flight.")

        # Rule 5: Vertex AI Model Garden Dynamic Routing
        r5_passed = self._check_keyword_in_ecosystem("vertex") or self._check_keyword_in_ecosystem("gemini-1.5")
        self._log_rule("Rule 5: Vertex AI Model Garden", r5_passed, "No decoupled 'Model Router' found in the Hub to dynamically evaluate constraints and assign Vertex models.")

        # Rule 6: Mandatory Ecosystem Inventory Pre-Flight
        r6_passed = self._check_inventory_preflight()
        self._log_rule("Rule 6: Inventory Pre-Flight", r6_passed, "Orchestrator jumps straight to planning without a mandatory 'Phase 0' code scan.")

        # Rule 9: 3-Tier Temporal Memory
        r9_passed = self._check_keyword_in_file("tooloo_v3_hub/organs/memory_organ/memory_logic.py", "fast") and \
                    self._check_keyword_in_file("tooloo_v3_hub/organs/memory_organ/memory_logic.py", "medium") and \
                    self._check_keyword_in_file("tooloo_v3_hub/organs/memory_organ/memory_logic.py", "long")
        self._log_rule("Rule 9: 3-Tier Memory", r9_passed, "Memory Organ schemas are structured around 'Tiers' (1, 2, 3), not temporal (Fast/Medium/Long).")

        # Rule 10: 6W Accountability
        r10_passed = self._check_keyword_in_file("tooloo_v3_hub/kernel/governance/stamping.py", "SixWProtocol")
        self._log_rule("Rule 10: 6W Accountability", r10_passed, "")

        # Rule 12: Autonomous Self-Healing
        r12_passed = self._check_keyword_in_file("tooloo_v3_hub/kernel/cognitive/ouroboros.py", "Ouroboros")
        self._log_rule("Rule 12: Ouroboros Sentinel", r12_passed, "")

        # Rule 13: Strict Physical Decoupling
        r13_passed = not (self.root / "tooloo_v3_hub" / "organs" / "claudio_organ").exists()
        self._log_rule("Rule 13: Strict Decoupling", r13_passed, "")
        
        # Rule 15: Zero-Footprint Exit
        r15_passed = self._check_keyword_in_file("tooloo_v3_hub/kernel/orchestrator.py", "gc.collect")
        self._log_rule("Rule 15: Zero-Footprint Exit", r15_passed, "Orchestrator does not actively enforce garbage collection or context purging.")
        
        # Rule 16: Prediction Delta Evaluation
        r16_passed = self._check_keyword_in_file("tooloo_v3_hub/kernel/orchestrator.py", "eval_prediction_delta")
        self._log_rule("Rule 16: Prediction Delta", r16_passed, "Orchestrator lacks the mathematical verification of prediction vs actual success.")
        
        # 16D Mental Dimensions Verification
        r16D_passed = self._check_keyword_in_file("GEMINI.md", "efficiency") and self._check_keyword_in_file(".agents/workflows/gemini.md", "financial")
        self._log_rule("Constitution: 16D Mental Dimensions", r16D_passed, "Holistic 16D cognitive scale is not deployed correctly in the Constitutional files.")

        total = len(self.report["rules"])
        passed = sum(1 for v in self.report["rules"].values() if v["status"] == "PASS")
        self.report["compliance_score"] = float(passed) / total
        
        with open("tooloo_v3_hub/psyche_bank/constitution_audit_results.json", "w") as f:
            json.dump(self.report, f, indent=2)
            
        print(f"\nIntrospection Complete. Found {total-passed} Constitutional Violations.")
        print("Details saved to psyche_bank/constitution_audit_results.json")

    def _log_rule(self, name: str, passed: bool, gap_reason: str):
        self.report["rules"][name] = {
            "status": "PASS" if passed else "FAIL",
            "gap": gap_reason if not passed else None
        }

    def _check_keyword_in_file(self, rel_path: str, keyword: str) -> bool:
        path = self.root / rel_path
        if not path.exists(): return False
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().lower()
            return keyword.lower() in content

    def _check_keyword_in_ecosystem(self, keyword: str) -> bool:
        exts = [".py", ".json", ".md"]
        for p in self.root.rglob("*"):
            if p.is_file() and p.suffix in exts:
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        if keyword.lower() in f.read().lower():
                            return True
                except: pass
        return False

    def _check_mandatory_jit(self) -> bool:
        # Check if JIT is forced universally in orchestrator
        path = self.root / "tooloo_v3_hub/kernel/orchestrator.py"
        if not path.exists(): return False
        content = path.read_text().lower()
        if "phase 0" in content and "mandatory" in content:
            return True
        return False

    def _check_inventory_preflight(self) -> bool:
        path = self.root / "tooloo_v3_hub/kernel/orchestrator.py"
        if not path.exists(): return False
        return "inventory" in path.read_text().lower()

if __name__ == "__main__":
    auditor = ConstitutionAuditor(".")
    auditor.scan_ecosystem()