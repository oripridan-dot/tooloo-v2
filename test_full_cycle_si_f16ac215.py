import pytest
from full_cycle_si_f16ac215 import process_data, complex_calculation

def test_complex_calculation_empty():
    assert complex_calculation([]) == 0

def test_complex_calculation_positive():
    assert complex_calculation([1, 2, 3]) == 14 # (1*1 + 2*2 + 3*3) % 100 + 3 * 5 = 14 + 15 = 29

def test_complex_calculation_zero():
    assert complex_calculation([0, 0]) == 0

def test_process_data_empty():
    assert process_data([]) == []

def test_process_data_mixed():
    input_data = [[1, 2], [3, 4, 5], []]
    # complex_calculation([1, 2]) = (1 + 4) % 100 + 2 * 5 = 5 + 10 = 15
    # complex_calculation([3, 4, 5]) = (9 + 16 + 25) % 100 + 3 * 5 = 50 + 15 = 65
    # complex_calculation([]) = 0
    assert process_data(input_data) == [15, 65, 0]
