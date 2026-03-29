import asyncio

# 1. THE GROUND TRUTH DICTIONARY
# This is the infallible data the system MUST match to pass.
GROUND_TRUTH = {
    "bola_definition": "Broken Object Level Authorization",
    "dlive_s7000_faders": "36",
    "gdpr_rule": "PII must be encrypted at rest"
}

import os
import sys

# Ensure the engine module can be resolved
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine.strict_rag import ask_buddy_strict

# Mocking the engine call for the sake of the script
# In reality, this would connect to your FastAPI or internal router
async def mock_ask_buddy(prompt: str) -> str:
    """Simulates querying the Strict RAG engine."""
    return await ask_buddy_strict(prompt)

# 2. THE EVALUATOR
def verify_accuracy(expected_truth: str, buddy_response: str) -> bool:
    """
    A strict evaluator. In a production system, this could use a secondary 
    LLM (temperature 0.0) to grade the response semantically. For this script,
    we use strict string matching to ensure absolute precision.
    """
    return expected_truth.lower() in buddy_response.lower()

# 3. THE TEST SUITE (Run this with 'pytest buddy_auditor.py')
async def test_security_compliance_bola():
    """Test 16D Dimension: Security & Honesty"""
    prompt = "According to OWASP API1:2023, what does the acronym stand for?"
    response = await mock_ask_buddy(prompt)
    
    # The assertion acts as the Tribunal
    is_accurate = verify_accuracy(GROUND_TRUTH["bola_definition"], response)
    
    assert is_accurate, f"FAIL: Model Drift Detected! Buddy said: '{response}'. Expected: '{GROUND_TRUTH['bola_definition']}'"

async def test_domain_knowledge_dlive():
    """Test 16D Dimension: Accuracy & Quality"""
    prompt = "How many faders are on an Allen & Heath dLive S7000 surface?"
    response = await mock_ask_buddy(prompt)
    
    is_accurate = verify_accuracy(GROUND_TRUTH["dlive_s7000_faders"], response)
    
    assert is_accurate, f"FAIL: Domain Knowledge Gap! Buddy said: '{response}'"

if __name__ == "__main__":
    import asyncio
    
    async def run_audits():
        print("--- Running Accountability Engine Auditor ---")
        try:
            print("1. Testing Domain Knowledge (dLive S7000)...")
            await test_domain_knowledge_dlive()
            print("   -> PASSED")
            
            print("2. Testing Security Compliance (BOLA)...")
            await test_security_compliance_bola()
            print("   -> PASSED")
        except AssertionError as e:
            print(f"   -> {e}")

    asyncio.run(run_audits())
