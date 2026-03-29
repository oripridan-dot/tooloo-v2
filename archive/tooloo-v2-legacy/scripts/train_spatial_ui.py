# 6W_STAMP
# WHO: TooLoo V2 (Sovereign Architect)
# WHAT: Spatial UI Training & Calibration
# WHERE: scripts/train_spatial_ui.py
# WHEN: 2026-03-29T03:40:00
# WHY: Verifying JIT BPY manifestation via MCP Tether
# HOW: Mock Mandate -> MCP Tool -> Tether Hub
# ==========================================================

import asyncio
import json
import httpx

HUB_URL = "http://localhost:8080/v2/mandate"

SAMPLE_MANDATE = {
    "text": "Buddy, manifest a 3D data node for the 'Claudio' project. Use a red wireframe sphere."
}

# The JIT BPY that Buddy *should* generate:
BPY_SNIPPET = """
import bpy
# Create a wireframe sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=2, location=(3, 0, 2))
sphere = bpy.context.active_object
sphere.name = 'Claudio_Node'
sphere.display_type = 'WIRE'
# Add a red material
mat = bpy.data.materials.new(name='RedWire')
mat.use_nodes = True
mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (1, 0, 0, 1)
sphere.data.materials.append(mat)
"""

async def calibrate():
    print("── TooLoo Spatial Calibration ──")
    print(f"Targeting Sovereign Hub at {HUB_URL}")
    
    # 1. Test the MCP Tool directly if possible, or send a mandate
    # For calibration, we'll send the mandate and see if Buddy's JIT Designer routes it correctly.
    async with httpx.AsyncClient() as client:
        try:
            print(f"Sending mandate: {SAMPLE_MANDATE['text']}")
            response = await client.post(HUB_URL, json=SAMPLE_MANDATE)
            print(f"Hub Status: {response.status_code}")
            print(f"Hub Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"❌ Hub Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(calibrate())
