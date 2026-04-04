import json
import os

REGISTRY_PATH = "/Users/oripridan/ANTIGRAVITY/tooloo-v2/tooloo_v4_hub/psyche_bank/model_garden_registry.json"

def harden_registry():
    if not os.path.exists(REGISTRY_PATH):
        print("Registry not found.")
        return

    with open(REGISTRY_PATH, "r") as f:
        data = json.load(f)

    # 1. Broad Cleanup (Remove placeholders)
    for provider in data["models"]:
        for m in data["models"][provider]:
            caps = m.get("capabilities", {})
            # Remove dummy user-added metrics
            caps.pop("Speed", None)
            caps.pop("Syntax_Precision", None)
            caps.pop("Constitutional", None)

    # 2. SOTA Injection (Reality-Based Metrics)
    sota_overrides = {
        "anthropic": [
            {
                "id": "claude-3-5-sonnet-20240620",
                "tier": "sovereign",
                "task": "coding",
                "cost_per_1M": 3.0,
                "capabilities": {
                    "logic": 0.99,
                    "coding": 0.99,
                    "constitutional": 0.98,
                    "creative": 0.95
                }
            }
        ],
        "openai": [
            {
                "id": "gpt-4o",
                "tier": "sota",
                "task": "general",
                "cost_per_1M": 5.0,
                "capabilities": {
                    "logic": 0.97,
                    "coding": 0.95,
                    "creative": 0.98,
                    "vision": 0.99,
                    "constitutional": 0.92
                }
            }
        ],
        "meta": [
            {
                "id": "meta/llama3-3@llama-3.3-70b-instruct",
                "tier": "efficient",
                "task": "reasoning",
                "cost_per_1M": 0.2,
                "capabilities": {
                    "logic": 0.93,
                    "coding": 0.88,
                    "constitutional": 0.85,
                    "efficiency": 0.98
                }
            }
        ],
        "google": [
            {
                "id": "gemini-1.5-pro",
                "tier": "sovereign",
                "task": "reasoning",
                "cost_per_1M": 3.5,
                "capabilities": {
                    "logic": 0.95,
                    "vision": 0.96,
                    "context": 1.00,
                    "constitutional": 0.90
                }
            }
        ]
    }

    # Apply Overrides
    for provider, sota_list in sota_overrides.items():
        if provider in data["models"]:
            for sota in sota_list:
                # Find and update or add
                found = False
                for idx, m in enumerate(data["models"][provider]):
                    if m["id"] == sota["id"]:
                        data["models"][provider][idx].update(sota)
                        found = True
                        break
                if not found:
                    data["models"][provider].insert(0, sota)

    # 3. Final Persistence
    with open(REGISTRY_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print("Registry Hardened: SOTA metrics injected and placeholders purged.")

if __name__ == "__main__":
    harden_registry()
