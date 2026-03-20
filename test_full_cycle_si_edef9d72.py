import pytest
import subprocess
import sys

def test_process_data_non_empty():
    data = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
    expected_averages = [2.0, 5.0]
    # Simulate running the script in a subprocess
    process = subprocess.run([sys.executable, 'full-cycle-si-edef9d72.py'], capture_output=True, text=True, timeout=60)
    assert process.returncode == 0
    # Parse stdout to get the result. This is brittle and depends on the exact print format.
    # A more robust solution would involve having the script return structured data.
    output_line = process.stdout.strip().split('\n')[-1]
    averages_str = output_line.split(': ')[1].replace('[', '').replace(']', '').split(', ')
    actual_averages = [float(x) for x in averages_str]
    assert actual_averages == expected_averages

def test_process_data_empty_row():
    data = [[], [1.0, 2.0]]
    expected_averages = [0.0, 1.5]
    process = subprocess.run([sys.executable, 'full-cycle-si-edef9d72.py'], capture_output=True, text=True, timeout=60)
    assert process.returncode == 0
    output_line = process.stdout.strip().split('\n')[-1]
    averages_str = output_line.split(': ')[1].replace('[', '').replace(']', '').split(', ')
    actual_averages = [float(x) for x in averages_str]
    assert actual_averages == expected_averages

def test_process_data_empty_input():
    data = []
    expected_averages = []
    # This test assumes the script handles empty input gracefully and prints 'Averages: []'
    process = subprocess.run([sys.executable, 'full-cycle-si-edef9d72.py'], capture_output=True, text=True, timeout=60)
    assert process.returncode == 0
    output_line = process.stdout.strip().split('\n')[-1]
    averages_str = output_line.split(': ')[1].replace('[', '').replace(']', '').split(', ')
    # Handle case where output might be '[]' for empty list
    if averages_str == ['']:
        actual_averages = []
    else:
        actual_averages = [float(x) for x in averages_str]
    assert actual_averages == expected_averages
