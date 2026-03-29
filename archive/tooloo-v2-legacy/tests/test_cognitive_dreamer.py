import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from engine.cognitive_dreamer import CognitiveDreamer, DreamReport

@pytest.fixture
def mocks():
    return {
        "vector_store": MagicMock(),
        "psyche_bank": MagicMock(),
        "model_garden": AsyncMock()
    }

@pytest.mark.asyncio
@patch('engine.cognitive_dreamer.Validator16D')
async def test_dream_cycle_extracts_insight(mock_validator_cls, mocks):
    mock_val_inst = MagicMock()
    mock_val_result = MagicMock()
    mock_val_result.autonomous_gate_pass = True
    mock_val_inst.validate.return_value = mock_val_result
    mock_validator_cls.return_value = mock_val_inst
    mocks["vector_store"].search.return_value = [MagicMock(content="Event A", id="1"), MagicMock(content="Event B", id="2")]
    mocks["model_garden"].call.return_value = "Always purge old caches before rebuilding."
    
    dreamer = CognitiveDreamer(**mocks)
    report = await dreamer.run_dream_cycle()
    
    assert report.garbage_purged_count == 0
    assert report.consolidated_count == 0
    mocks["psyche_bank"].capture.assert_called_once()

@pytest.mark.asyncio
@patch('engine.cognitive_dreamer.Validator16D')
async def test_dream_cycle_purges_garbage(mock_validator_cls, mocks):
    mocks["vector_store"].search.return_value = [MagicMock(content="Garbage A", id="1"), MagicMock(content="Garbage B", id="2")]
    mocks["model_garden"].call.return_value = "Noise <PURGE>"
    
    dreamer = CognitiveDreamer(**mocks)
    report = await dreamer.run_dream_cycle()
    
    assert report.garbage_purged_count == 2
    assert report.consolidated_count == 0
    assert mocks["vector_store"].remove.call_count == 2

@pytest.mark.asyncio
@patch('engine.cognitive_dreamer.Validator16D')
async def test_dream_cycle_consolidates_memories(mock_validator_cls, mocks):
    mocks["vector_store"].search.return_value = [MagicMock(content="Old thought A", id="1"), MagicMock(content="Old thought B", id="2")]
    mocks["model_garden"].call.return_value = "Needs storage <CONSOLIDATE>"
    
    dreamer = CognitiveDreamer(**mocks)
    report = await dreamer.run_dream_cycle()
    
    assert report.garbage_purged_count == 0
    assert report.consolidated_count == 2
    assert mocks["vector_store"].add.call_count == 1
    assert mocks["vector_store"].remove.call_count == 2
