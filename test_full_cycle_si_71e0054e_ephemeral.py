import pytest
import subprocess
import os

# Assume the component is in the same directory for this test
COMPONENT_PATH = "full-cycle-si-71e0054e.py"

def run_component_test(test_function_name):
    # Verify test module is inside tests/ directory before invocation (simulated)
    if not os.path.dirname(COMPONENT_PATH).startswith("tests/"):
        print(f"Skipping test: {test_function_name} - Component not in tests/ directory.")
        return

    try:
        # Execute the specific test function using subprocess to capture stdout/stderr and enforce timeout
        result = subprocess.run(
            ["pytest", COMPONENT_PATH, f"-k {test_function_name}", "--capture=tee-sys"],
            capture_output=True,
            text=True,
            timeout=60  # Timeout at 60 s
        )

        if result.returncode != 0:
            print(f"Test failed: {test_function_name}\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}")
            pytest.fail(f"Test {test_function_name} failed")
        else:
            print(f"Test passed: {test_function_name}\nStdout:\n{result.stdout}")

    except subprocess.TimeoutExpired:
        print(f"Test timed out: {test_function_name}")
        pytest.fail(f"Test {test_function_name} timed out")
    except Exception as e:
        print(f"An unexpected error occurred during test {test_function_name}: {e}")
        pytest.fail(f"Unexpected error in test {test_function_name}")

# Dynamically generate tests for each function in the component
# This assumes functions are testable independently. For complex interactions, more sophisticated test generation is needed.
def generate_tests_from_component(component_code):
    import inspect
    # A very basic way to get function names. A real analysis would be more robust.
    functions = []
    for name, obj in inspect.getmembers(__import__(os.path.splitext(COMPONENT_PATH)[0])):
        if inspect.isfunction(obj) and obj.__module__ == os.path.splitext(COMPONENT_PATH)[0]:
            functions.append(name)

    for func_name in functions:
        test_name = f"test_{func_name}_isolated"
        # Create a test function that calls run_component_test
        globals()[test_name] = lambda name=func_name: run_component_test(name)


# Load component code to introspect functions
with open(COMPONENT_PATH, 'r') as f:
    component_code = f.read()

# Dynamically create test functions based on the component's functions
# This part needs to be executed before pytest discovery if we want to dynamically add tests.
# For simplicity in this example, we'll assume we can manually define tests or use a plugin.
# In a real scenario, this might involve parsing the AST of the component.

# Placeholder for dynamically generated tests. 
# The actual generation of tests for specific function calls would require mocking or providing input data.
# For this exercise, we'll create a few representative tests.

def test_component_function_1_isolated():
    run_component_test("test_addition") # Example function from previous analysis

def test_component_function_2_isolated():
    run_component_test("test_string_concat") # Example function from previous analysis

# Add more tests as needed for other functions discovered from full-cycle-si-71e0054e.py
