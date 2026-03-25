import pytest
from unittest.mock import patch, MagicMock
from engine.cognitive_middleware import CognitiveMiddleware, CognitiveState

@pytest.fixture
def middleware():
    return CognitiveMiddleware()

def test_analyze_mandate_success_gemini(middleware):
    mock_resp = MagicMock()
    mock_resp.text = '''```json
{
  "intent": "REFACTOR",
  "timeframe": "Meso",
  "dimensions": {"Architectural_Foresight": 0.95}
}
```'''
    
    with patch("engine.cognitive_middleware._gemini_client") as mock_gemini:
        mock_gemini.models.generate_content.return_value = mock_resp
        
        state = middleware.analyze_mandate("Refactor the entire core engine")
        assert state.intent == "REFACTOR"
        assert state.timeframe == "Meso"
        assert state.dimensions["Architectural_Foresight"] == 0.95

def test_analyze_mandate_fallback(middleware):
    """Test that a failure in the LLM call returns the sensible default."""
    with patch("engine.cognitive_middleware._gemini_client") as mock_gemini:
        mock_gemini.models.generate_content.side_effect = Exception("API Engine Failure")
        with patch("engine.cognitive_middleware._vertex_client", None):
            state = middleware.analyze_mandate("Fix the micro bug")
            assert state.intent == "EXECUTE"
            assert state.timeframe == "Meso"
            assert state.dimensions["Architectural_Foresight"] == 0.8
