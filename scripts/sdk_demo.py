import asyncio
import logging
import uuid
import sys
import os

# Add src to sys.path to allow importing the sdk
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from sdk import TooLooClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SDKDemo")

async def run_demo():
    """Run a full demonstration of the TooLoo V2 SDK."""
    print("\n🌟 TooLOO V2: SDK Demonstration 🌟\n")
    
    # 1. Initialize Client
    async with TooLooClient(base_url="http://localhost:8000") as client:
        session_id = f"demo-{uuid.uuid4().hex[:4]}"
        print(f"📡 Connected to TooLoo Engine (Session: {session_id})")
        
        # 2. Test Unary Execution
        print("\n--- [Test 1: Unary Execution] ---")
        prompt = "Explain the 6W Cognitive Coordinate system briefly."
        print(f"Request: {prompt}")
        
        try:
            response = await client.execute(prompt=prompt, session_id=session_id)
            print(f"Response: {response.response}")
            print(f"Latency: {response.latency_ms:.2f}ms | Violations: {len(response.violations)}")
        except Exception as e:
            print(f"❌ Execution Failed: {e}")

        # 3. Test Streaming
        print("\n--- [Test 2: Token Streaming] ---")
        stream_prompt = "Generate a short blueprint for an autonomous drone swarm."
        print(f"Request: {stream_prompt}")
        
        print("Tokens: ", end="", flush=True)
        try:
            async for chunk in client.stream(prompt=stream_prompt, session_id=session_id):
                print(chunk, end="", flush=True)
            print("\n✅ Stream Finished")
        except Exception as e:
            print(f"\n❌ Streaming Failed: {e}")

if __name__ == "__main__":
    # Ensure uvicorn is running in another process before running this
    # uvicorn src.api.main:app
    asyncio.run(run_demo())
