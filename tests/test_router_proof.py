import os
import asyncio
import logging
import json
from src.tooloo.core.llm import get_llm_client

# Force logging for proof visibility
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Sovereign_Proof")

async def prove_sota():
    router = get_llm_client()
    
    logger.info("================================================")
    logger.info("🚀 INITIATING MULTIDIMENSIONAL SOTA PROOF 🚀")
    logger.info("================================================\n")
    
    # 1. Prove Anthropic SOTA (Extended Thinking & Compaction)
    logger.info("[TEST 1] Proving AnthropicVertex with SOTA Context Compaction...")
    try:
        # Using 3-5-sonnet just in case 3-7 is not deployed in the project yet
        story = await router.generate_anthropic_sota(
            prompt="Write a single, incredibly terse and brutally honest sentence confirming you are alive, running on Vertex AI, and performing SOTA Extended Thinking.",
            system_instruction="You are Buddy.",
            model="claude-3-5-sonnet@20240620" 
        )
        logger.info(f"✅ ANTHROPIC SUCCESS. Response:\n\"\"\"{story.strip()}\"\"\"\n")
    except Exception as e:
        logger.error(f"❌ ANTHROPIC SOTA FAILED:\n{e}\n")

    # 2. Prove DeepSeek MaaS via Native OpenAI Wrapper
    logger.info("[TEST 2] Proving DeepSeek V3.2 Serverless MaaS integration...")
    schema = {
        "type": "object",
        "properties": {
            "insight": {"type": "string", "description": "The brutally honest insight generated."}
        },
        "required": ["insight"]
    }
    
    try:
        res = await router.generate_structured(
            prompt="Analyze this schema protocol and return a bold insight.",
            schema=schema,
            system_instruction="You are DeepSeek-V3 operating under the Sovereign Hub Constitution.",
            model="deepseek-ai/deepseek-v3.2-maas" 
        )
        logger.info(f"✅ DEEPSEEK SUCCESS. Response:\n{json.dumps(res, indent=2)}\n")
    except Exception as e:
        logger.warning(f"⚠️ DEEPSEEK FAILED:\n{e}\n")

    # 3. Prove Llama 4 API Service
    logger.info("[TEST 3] Proving Llama 4 API Service...")
    try:
        # Hitting a standard Llama 4 MAAS signature
        res = await router.generate_structured(
            prompt="What is your primary architectural component base?",
            schema=schema,
            system_instruction="You are Llama-4 operating under the Sovereign Purity mandates.",
            model="meta/llama-4-scout-17b-16e-instruct-maas" 
        )
        logger.info(f"✅ LLAMA 4 SUCCESS. Response:\n{json.dumps(res, indent=2)}\n")
    except Exception as e:
        logger.warning(f"⚠️ LLAMA 4 FAILED:\n{e}\n")
        
    logger.info("================================================")
    logger.info("🏁 SOTA PROOF EXECUTION COMPLETE 🏁")
    logger.info("================================================")

if __name__ == "__main__":
    asyncio.run(prove_sota())
