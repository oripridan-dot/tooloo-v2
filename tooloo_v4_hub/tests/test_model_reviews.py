import asyncio
import os
import httpx
from dotenv import load_dotenv

async def gather_reviews():
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY not found in environment.")
        return

    prompt = """
    You are a SOTA AI evaluating 'Tooloo V4' and its 'Sovereign Buddy Agent'.
    Tooloo V4 recently integrated a Multi-Model 'Garden Routing' algorithm that dynamically dispatches 
    tasks to different AI models based on multidimensional intent vectors (Logic, Speed, Vision) 
    while balancing execution cost through a logarithmic financial penalty protocol.
    
    Please provide:
    1. A brief review of this dynamic multi-agent capability and Buddy's role as the Sovereign orchestrator.
    2. Two strictly technical engineering suggestions to improve its dynamic routing architecture or JIT telemetry flow.
    
    Keep the response concise (2 paragraphs max). Begin your response with [YOUR INTERNAL MODEL NAME].
    """

    models_to_test = [
        ("Gemini 2.5 Pro (Heavy Reasoning Tier)", "gemini-2.5-pro"),
        ("Gemini 2.5 Flash (High-Speed Execution Tier)", "gemini-2.5-flash")
    ]
    
    print("=== COMMENCING GLOBAL SOTA REVIEW PULSE ===\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for name, model_id in models_to_test:
            print(f"\n[DISPATCHING TO: {name} | {model_id}]")
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
                payload = {
                    "contents": [{"parts":[{"text": prompt}]}]
                }
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                print(f"\n{text}\n")
            except Exception as e:
                import traceback
                print(f"Error communicating with {model_id}: {str(e)}\n{traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(gather_reviews())
