import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from tooloo_v4_hub.organs.financial_organ.financial_logic import get_financial_logic

def seed_ledger():
    fin = get_financial_logic()
    # Simulated costs from previous round stress test
    fin.log_mission_cost("anthropic", "claude-3-5-sonnet-20240620", 4096, 3.0)
    fin.log_mission_cost("google", "gemini-1.5-pro", 8192, 3.5)
    fin.log_mission_cost("openai", "gpt-4o", 2048, 5.0)
    fin.log_mission_cost("meta", "meta/llama3-3@llama-3.3-70b-instruct", 1024, 0.2)
    print("Financial Ledger seeded with SOTA mission data.")

if __name__ == "__main__":
    seed_ledger()
