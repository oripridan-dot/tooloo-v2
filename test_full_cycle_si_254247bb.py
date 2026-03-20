import pytest
import subprocess

# Mock the _run_command function to control its behavior
class MockCompletedProcess:
    def __init__(self, stdout, stderr):
        self.stdout = stdout.encode('utf-8')
        self.stderr = stderr.encode('utf-8')

    def communicate(self):
        return self.stdout, self.stderr

def mock_run_command(command):
    if command == ['echo', 'Processing:', 'sample_input']:
        return "Processed: Processing: sample_input\n", ""
    else:
        return "", f"Unknown command: {command}"

def test_process_data_success():
    # Temporarily patch subprocess.Popen to use our mock
    original_popen = subprocess.Popen
    subprocess.Popen = lambda cmd, stdout, stderr: MockCompletedProcess(stdout='Processing: sample_input\n', stderr='')
    
    try:
        # Import the function to test after patching
        from full_cycle_si_254247bb import process_data
        result = process_data('sample_input')
        assert result == "Processed: Processing: sample_input"
    finally:
        # Restore the original Popen
        subprocess.Popen = original_popen

def test_process_data_error():
    # Temporarily patch subprocess.Popen to simulate an error
    original_popen = subprocess.Popen
    subprocess.Popen = lambda cmd, stdout, stderr: MockCompletedProcess(stdout='', stderr='Error executing command')

    try:
        from full_cycle_si_254247bb import process_data
        result = process_data('sample_input')
        assert result == "Error: Error executing command"
    finally:
        subprocess.Popen = original_popen

