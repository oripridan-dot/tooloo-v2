import sys
sys.path.insert(0, '/Users/oripridan/ANTIGRAVITY/tooloo-v2')
from engine.router import MandateRouter, LockedIntent
from dataclasses import fields

print(f"MandateRouter has apply_jit_boost: {hasattr(MandateRouter, 'apply_jit_boost')}")
print(f"LockedIntent fields: {[f.name for f in fields(LockedIntent)]}")
