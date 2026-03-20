import pytest
from full_cycle_si_9bf27ae8 import longest_common_prefix

def test_empty_list():
    assert longest_common_prefix([]) == ""

def test_single_string():
    assert longest_common_prefix(["apple"]) == "apple"

def test_no_common_prefix():
    assert longest_common_prefix(["dog", "racecar", "car"]) == ""

def test_common_prefix_at_beginning():
    assert longest_common_prefix(["flower", "flow", "flight"]) == "fl"

def test_all_same_string():
    assert longest_common_prefix(["test", "test", "test"]) == "test"

def test_common_prefix_with_empty_string():
    assert longest_common_prefix(["", "abc"]) == ""

def test_common_prefix_with_empty_string_first():
    assert longest_common_prefix(["abc", ""]) == ""

def test_common_prefix_mixed():
    assert longest_common_prefix(["apple", "apricot", "ape"]) == "ap"
