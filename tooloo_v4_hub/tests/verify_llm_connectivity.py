import os
import requests
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def verify_gemini_rest():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found in .env")
        return
        
    print(f"📡 Testing API Key: {api_key[:10]}...")
    
    # Test multiple models to see what's available
    models = ["models/gemini-1.5-flash-latest", "models/gemini-2.0-flash-exp", "models/gemini-2.0-flash"]
    
    for model in models:
        print(f"\n--- Checking {model} ---")
        url = f"https://generativelanguage.googleapis.com/v1/{model}:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": "Hello."}]}]
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            data = response.json()
            
            if "candidates" in data:
                print(f"✅ SUCCESS: {model} is operational.")
            else:
                print(f"❌ FAILED: {data.get('error', {}).get('message', 'Unknown error')}")
                # Check for 401 specifically
                if response.status_code == 401:
                    print("🚨 CRITICAL: API Key is invalid or expired.")
        except Exception as e:
            print(f"❌ CONNECTION ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(verify_gemini_rest())
