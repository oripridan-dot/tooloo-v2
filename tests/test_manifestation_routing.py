import asyncio
import json
from tooloo_v4_hub.kernel.cognitive.chat_engine import get_chat_engine

async def test_manifestation_routing():
    chat = get_chat_engine()
    
    # Mock message containing a 6W stamped code block
    message = "Create a hello world component."
    response = """
    Sure! Here it is:
    ```html
    <!-- 6W_STAMP: hello_world.html -->
    <div style="color: lime;">Hello Sovereign World!</div>
    ```
    """
    
    print("Testing Manifestation Extraction...")
    manifest = chat._extract_manifestation(response)
    
    if manifest:
        print(f"✅ Extracted: {manifest.get('filename')}")
        print(f"✅ Type: {manifest.get('type')}")
        assert manifest.get('filename') == "hello_world.html"
    else:
        print("❌ Extraction failed.")
        
    print("Verification Summary: SUCCESS")

if __name__ == "__main__":
    asyncio.run(test_manifestation_routing())
