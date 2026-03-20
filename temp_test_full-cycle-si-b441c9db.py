import pytest
import os
import sys

# Ensure the directory containing the module is in sys.path
# This is a placeholder and might need adjustment based on actual project structure
module_dir = os.path.dirname(os.path.abspath('full-cycle-si-b441c9db'))
sys.path.insert(0, module_dir)

# Attempt to import the module. This might fail if the module is not importable directly
try:
    from full_cycle_si_b441c9db import analyze_dependencies
except ImportError as e:
    # If direct import fails, try to find the module in a common structure like 'src'
    # This is a heuristic and may need to be adapted.
    if 'full-cycle-si-b441c9db' in sys.modules:
        from full_cycle_si_b441c9db import analyze_dependencies
    else:
        # Fallback: Try to import by a cleaned-up name if the file name is unusual
        try:
            from analyze_dependencies_module import analyze_dependencies # Assuming a renamed module
        except ImportError:
            pytest.fail(f"Could not import analyze_dependencies from full-cycle-si-b441c9db. Error: {e}")


def test_analyze_dependencies_vulnerable():
    dependencies = [
        {"name": "requests", "version": "2.25.0"},
        {"name": "flask", "version": "1.1.1"}
    ]
    expected_risks = {
        "vulnerable_versions": ["requests@2.25.0"],
        "license_issues": [],
        "outdated_versions": []
    }
    assert analyze_dependencies(dependencies) == expected_risks

def test_analyze_dependencies_license():
    dependencies = [
        {"name": "django", "version": "3.0.0"},
        {"name": "flask", "version": "1.1.1"}
    ]
    expected_risks = {
        "vulnerable_versions": [],
        "license_issues": ["django@3.0.0"],
        "outdated_versions": []
    }
    assert analyze_dependencies(dependencies) == expected_risks

def test_analyze_dependencies_outdated():
    dependencies = [
        {"name": "flask", "version": "1.1.1"},
        {"name": "requests", "version": "2.20.0"}
    ]
    expected_risks = {
        "vulnerable_versions": [],
        "license_issues": [],
        "outdated_versions": ["flask@1.1.1"]
    }
    assert analyze_dependencies(dependencies) == expected_risks

def test_analyze_dependencies_no_risks():
    dependencies = [
        {"name": "numpy", "version": "1.20.0"},
        {"name": "pandas", "version": "1.2.0"}
    ]
    expected_risks = {
        "vulnerable_versions": [],
        "license_issues": [],
        "outdated_versions": []
    }
    assert analyze_dependencies(dependencies) == expected_risks

def test_analyze_dependencies_mixed_risks():
    dependencies = [
        {"name": "requests", "version": "2.25.1"},
        {"name": "django", "version": "3.0.0"},
        {"name": "flask", "version": "1.1.1"}
    ]
    expected_risks = {
        "vulnerable_versions": ["requests@2.25.1"],
        "license_issues": ["django@3.0.0"],
        "outdated_versions": ["flask@1.1.1"]
    }
    assert analyze_dependencies(dependencies) == expected_risks

def test_analyze_dependencies_empty_list():
    dependencies = []
    expected_risks = {
        "vulnerable_versions": [],
        "license_issues": [],
        "outdated_versions": []
    }
    assert analyze_dependencies(dependencies) == expected_risks