import asyncio
import os
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))
except ImportError:
    pass

from tooloo_v4_hub.kernel.cognitive.llm_client import get_llm_client
from tooloo_v4_hub.organs.financial_organ.financial_logic import get_financial_logic

async def check_financial_stress():
    print("🚀 --- STARTING FINANCIAL STRESS TEST & MODEL METRICS ---")
    
    # 1. Inspect the Ledger Before
    ledger = get_financial_logic().ledger
    start_cost = ledger.get("total_cost_usd", 0.0)
    print(f"💰 Initial Ledger Total Coast: ${start_cost:.6f}")
    
    client = get_llm_client()
    
    # 2. Test Flash Route (Checking Default Alignment)
    print("\n[A] Executing standard 'Flash' Tier thought...")
    try:
        t0 = time.time()
        # provider='rest' is used to quickly bypass needing GCP credentials locally for the test
        ans_flash = await client.generate_thought(
            "Respond in one sentence: What is the Sovereign Hub?", 
            model_tier="flash", provider="rest"
        )
        t_flash = time.time() - t0
        print(f"⚡ Flash Response [{t_flash:.2f}s]: {ans_flash[:60]}...")
    except Exception as e:
        print(f"Flash Route Failed: {e}")

    # 3. Test Pro Route (Checking High-Fidelity SOTA alignment)
    print("\n[B] Executing SOTA 'Pro' Tier thought...")
    try:
        t0 = time.time()
        ans_pro = await client.generate_sota_thought(
            "Summarize the Autopoietic loop in two sentences.", 
            model_tier="pro"
        )
        t_pro = time.time() - t0
        print(f"🧠 Pro Response [{t_pro:.2f}s]: {ans_pro[:60]}...")
    except Exception as e:
        print(f"Pro Route Failed: {e}")
        
    # 4. Verify Financial Logging
    ledger_after = get_financial_logic().ledger
    end_cost = ledger_after.get("total_cost_usd", 0.0)
    diff = end_cost - start_cost
    print(f"\n💰 Final Ledger Total Cost: ${end_cost:.6f} (Delta: +${diff:.6f})")

if __name__ == "__main__":
    asyncio.run(check_financial_stress())
