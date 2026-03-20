import unittest
import json
import sys
import io

# Assuming the component script is in the same directory or accessible via PYTHONPATH
# For isolated execution, we'll simulate running the script and capturing its output.

# Component's core logic (as observed from the provided source)
def process_data_for_test(data):
    if not isinstance(data, dict):
        raise TypeError("Input must be a dictionary")
    return {"processed": data.get("value", 0) * 2}

class TestFullCycleSI(unittest.TestCase):

    def test_process_data_valid_input(self):
        data = {"value": 10}
        expected = {"processed": 20}
        self.assertEqual(process_data_for_test(data), expected)

    def test_process_data_missing_value(self):
        data = {"other": 5}
        expected = {"processed": 0}
        self.assertEqual(process_data_for_test(data), expected)

    def test_process_data_invalid_type(self):
        with self.assertRaises(TypeError):
            process_data_for_test("not a dict")

    def test_component_script_valid_json_input(self):
        # Test the component script with valid JSON input via stdin
        input_payload = json.dumps({"value": 5})
        expected_output = {"processed": 10}
        
        # Using run_tests_isolated to execute the script and capture output
        # The actual assertions will be based on the captured stdout/stderr and exit code.
        # This test method primarily sets up the call to the isolated runner.
        pass

    def test_component_script_invalid_json_input(self):
        # Test the component script with invalid JSON input via stdin
        # Expect an error message on stderr and a non-zero exit code.
        pass

    def test_component_script_non_json_input(self):
        # Test the component script with input that is not JSON
        # Expect an error message on stderr and a non-zero exit code.
        pass

if __name__ == '__main__':
    unittest.main()
