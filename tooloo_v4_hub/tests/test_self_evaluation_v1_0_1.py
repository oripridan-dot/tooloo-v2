# 6W_STAMP
# WHO: TooLoo V3 (Ouroboros Sentinel)
# WHAT: HEALED_TEST_SELF_EVALUATION.PY | Version: 1.0.1 | Version: 1.0.1
# WHERE: tooloo_v4_hub/tests/test_self_evaluation.py
# WHEN: 2026-04-04T00:41:42.399341+00:00
# WHY: Heal STAMP_MISSING and maintain architectural purity
# HOW: Ouroboros Non-Destructive Saturation
# TRUST: T3:arch-purity
# PURITY: 1.00
# ==========================================================

# WHO: TooLoo V4.2.0 (Sovereign Architect)
# WHAT: TEST_SELF_EVALUATION | Version: 1.0.0
# WHERE: tooloo_v4_hub/tests/test_self_evaluation.py
# WHY: Rule 16 - Verifying the Self-Evaluation and Calibration Pulse
# HOW: Mocked Mission History and File Audits
# PURITY: 1.00
# ==========================================================

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse import SelfEvaluationPulse

@pytest.mark.asyncio
async def test_self_evaluation_cycle_metrics():
    """Verifies that the evaluation cycle correctly aggregates metrics."""
    with patch("tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse.get_calibration_engine") as mock_cal, \
         patch("tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse.get_audit_agent") as mock_audit, \
         patch("tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse.SelfEvaluationPulse.perform_retrospective") as mock_retro, \
         patch("tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse.SelfEvaluationPulse.perform_purity_audit") as mock_purity:
        
        # Setup Mocks
        mock_audit_inst = MagicMock()
        mock_audit_inst.calculate_vitality_index = AsyncMock(return_value={"vitality": 1.0})
        mock_audit.return_value = mock_audit_inst
        
        mock_retro.return_value = {"mission_count": 5, "avg_eval_delta": 0.02}
        mock_purity.return_value = {"files_scanned": 10, "purity_index": 0.98}
        
        pulse = SelfEvaluationPulse()
        report = await pulse.run_evaluation_cycle()
        
        assert report["hub_vitality"] > 0.9
        assert report["avg_prediction_delta"] == 0.02
        assert report["purity_index"] == 0.98
        assert report["calibration_status"] == "PENDING"

@pytest.mark.asyncio
async def test_calibration_trigger_on_high_drift():
    """Verifies that calibration is triggered when drift exceeds the threshold."""
    with patch("tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse.get_calibration_engine") as mock_cal, \
         patch("tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse.get_audit_agent") as mock_audit, \
         patch("tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse.SelfEvaluationPulse.perform_retrospective") as mock_retro, \
         patch("tooloo_v4_hub.kernel.cognitive.self_evaluation_pulse.SelfEvaluationPulse.perform_purity_audit") as mock_purity:
        
        # Setup Mocks with High Drift (EVD > 0.05)
        mock_cal_inst = MagicMock()
        mock_cal_inst.refine_weights = AsyncMock()
        mock_cal.return_value = mock_cal_inst
        
        mock_audit_inst = MagicMock()
        mock_audit_inst.calculate_vitality_index = AsyncMock(return_value={"vitality": 1.0})
        mock_audit.return_value = mock_audit_inst
        
        mock_retro.return_value = {"mission_count": 5, "avg_eval_delta": 0.12} # 12% Drift
        mock_purity.return_value = {"files_scanned": 10, "purity_index": 0.98}
        
        pulse = SelfEvaluationPulse()
        report = await pulse.run_evaluation_cycle()
        
        assert report["calibration_status"] == "CALIBRATED"
        mock_cal_inst.refine_weights.assert_called_once()
