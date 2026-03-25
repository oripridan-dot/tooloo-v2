import pytest
from engine.intent_analyzer import IntentAnalyzer

def test_intent_analyzer_initialization():
    analyzer = IntentAnalyzer()
    assert analyzer.global_intent_vector is not None
    assert len(analyzer.global_intent_vector) == 4

def test_passive_listen_intent():
    analyzer = IntentAnalyzer()
    score, action = analyzer.analyze("I see the button is blue")
    
    # Due to lexical analysis, "see", "is", "button", "blue"
    # Should yield a low score mapped to LISTEN
    assert action == "LISTEN"
    assert score < 0.45

def test_active_execute_intent():
    analyzer = IntentAnalyzer()
    score, action = analyzer.analyze("make the button blue")
    
    # "make" triggers high agency, this should map to EXECUTE
    assert action == "EXECUTE"
    assert score > 0.75

def test_collaborative_exploration_intent():
    analyzer = IntentAnalyzer()
    score, action = analyzer.analyze("how does the pipeline work")
    
    # "how" triggers question words
    assert action == "COLLABORATE"
    assert 0.45 <= score <= 0.75

def test_cosine_similarity_math():
    analyzer = IntentAnalyzer()
    # Identical vectors should have a cosine similarity of 1.0
    v = [0.1, 0.2, 0.3, 0.4]
    sim = analyzer._cosine_similarity(v, v)
    assert round(sim, 5) == 1.00000
    
    # Orthogonal vectors should have a cosine similarity of 0.0
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    sim2 = analyzer._cosine_similarity(v1, v2)
    assert sim2 == 0.0
