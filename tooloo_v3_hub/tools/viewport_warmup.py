import asyncio
import websockets
import json

async def warmup():
    uri = "ws://localhost:8085/ws"
    async with websockets.connect(uri) as websocket:
        # 1. Manifest the 'Sovereign Foundation'
        print("[Warmup] Manifesting Nodes...")
        nodes = [
            {"type": "manifest", "id": "engram-01", "shape": "torus", "color": "0x00ccff"},
            {"type": "manifest", "id": "engram-02", "shape": "torus", "color": "0xff00ff"},
            {"type": "manifest", "id": "foundational-node", "shape": "cube", "color": "0x00ff88"}
        ]
        
        for node in nodes:
            await websocket.send(json.dumps(node))
            await asyncio.sleep(0.5)

        # 2. Wake up Buddy
        print("[Warmup] Waking up Buddy...")
        await websocket.send(json.dumps({
            "type": "buddy_directive",
            "directive": "wave"
        }))
        
        print("[Warmup] Complete. Viewport is now populated.")

if __name__ == "__main__":
    asyncio.run(warmup())
