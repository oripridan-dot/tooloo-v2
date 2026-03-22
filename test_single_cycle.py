from engine.self_improvement import SelfImprovementEngine
from engine.config import _COMPONENT_SOURCE

import os
# We want it to be considered LIVE, not PYTEST
if "PYTEST_CURRENT_TEST" in os.environ:
    del os.environ["PYTEST_CURRENT_TEST"]

engine = SelfImprovementEngine()
# Run 1 cycle with full loop
print("Running Phase Implementation test")
report = engine.run(run_regression_gate=True)
print("Finished!")
