import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.executor import JITExecutor, Envelope
from engine.fleet_manager import AutonomyDial, AutonomyLevel
from engine.psyche_bank import PsycheBank
from engine.intelligence.neo import NeoAgent
from engine.intelligence.trinity import TrinityAgent

class TestJITUXSOTA(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.executor = JITExecutor(None, None)
        self.psyche_bank_path = Path("/tmp/test_psyche_bank_ux.json")
        if self.psyche_bank_path.exists():
            self.psyche_bank_path.unlink()
        
        # Bypass initialization entirely
        self.psyche_bank = PsycheBank(self.psyche_bank_path)
        self.psyche_bank.__ainit__ = AsyncMock()
        self.psyche_bank.shutdown = AsyncMock()
        self.psyche_bank._initialized.set()
            
        self.neo = NeoAgent(self.executor)
        self.trinity = TrinityAgent(self.executor)

    async def asyncTearDown(self):
        if self.psyche_bank_path.exists():
            self.psyche_bank_path.unlink()

    async def test_intent_preview_generation(self):
        """Verify that Intent Preview is correctly generated for a mission."""
        envelopes = [
            Envelope(
                mandate_id="test-1",
                intent="Refactor UI headers",
                domain="ui",
                metadata={"files_affected": ["index.html"]}
            )
        ]
        preview = self.executor.generate_intent_preview(envelopes)
        self.assertIn("Intent Preview", preview)
        self.assertIn("Refactor UI headers", preview)
        self.assertIn("index.html", preview)

    async def test_autonomy_gating(self):
        """Verify that high-risk tasks are gated by the AutonomyDial."""
        envelopes = [
            Envelope(
                mandate_id="test-gate",
                intent="Modify database schema",
                domain="database",
                metadata={"approved": False}
            )
        ]
        
        # Should raise PermissionError because 'approved' is False for a high-risk domain
        with self.assertRaises(PermissionError):
            await self.executor.fan_out(lambda x: x, envelopes)

    async def test_approved_execution(self):
        """Verify that tasks proceed if approved."""
        envelopes = [
            Envelope(
                mandate_id="test-ok",
                intent="Non-destructive UI tweak",
                domain="ui",
                metadata={"approved": True}
            )
        ]
        results = await self.executor.fan_out(lambda x: "Done", envelopes)
        self.assertEqual(results[0].status, "Success")

    async def test_acceptance_ratio_tracking(self):
        """Verify ROI metric persistence in PsycheBank."""
        # Manually inject history since we bypassed initialization
        self.psyche_bank._acceptance_history = []
        
        roi = await self.psyche_bank.update_acceptance_ratio(
            mandate_id="m-1",
            accepted=True,
            modified_lines=10,
            domain="ui",
            rationale="Aligned with brand tokens"
        )
        self.assertEqual(roi, 1.0)
        
        roi2 = await self.psyche_bank.update_acceptance_ratio(
            mandate_id="m-2",
            accepted=False,
            modified_lines=50,
            domain="core",
            rationale="Incorrect logic loop"
        )
        self.assertEqual(roi2, 0.5)

if __name__ == "__main__":
    unittest.main()
