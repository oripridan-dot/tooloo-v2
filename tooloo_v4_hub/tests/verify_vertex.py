import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def verify_vertex():
    import vertexai
    from vertexai.generative_models import GenerativeModel
    
    project = os.getenv("GCP_PROJECT_ID", "too-loo-zi8g7e")
    location = "us-central1"
    
    print(f"🔧 Initializing Vertex AI in project '{project}', location '{location}'...")
    
    try:
        vertexai.init(project=project, location=location)
        print("✅ Vertex AI initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize Vertex AI: {e}")
        return

    models_to_test = [
        "gemini-1.5-pro",
        "gemini-2.5-pro"
    ]
    
    for model_name in models_to_test:
        print(f"\n--- Testing Model: {model_name} ---")
        try:
            model = GenerativeModel(model_name)
            response = model.generate_content("Describe yourself in 5 words.")
            print(f"✅ SUCCESS: {model_name} replied: {response.text.strip()}")
        except Exception as e:
            print(f"❌ FAILED for {model_name}: {e}")

if __name__ == "__main__":
    asyncio.run(verify_vertex())
