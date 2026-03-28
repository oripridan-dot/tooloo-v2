import os
import sys

# Simulate app.py anchor
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print(f"Adding root to path: {root}")
sys.path.insert(0, root)

try:
    print("Testing 'from scripts.claudio_upscaler import tooloo_prove_identity'...")
    from scripts.claudio_upscaler import tooloo_prove_identity
    print("SUCCESS!")
except Exception as e:
    print(f"FAILURE: {e}")
    import traceback
    traceback.print_exc()
