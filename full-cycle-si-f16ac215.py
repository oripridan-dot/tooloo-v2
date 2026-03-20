from typing import List

def complex_calculation(data: List[int]) -> int:
    """Performs a series of calculations on a list of integers."""
    if not data:
        return 0
    
    intermediate = sum(x * x for x in data)
    result = intermediate % 100 + len(data) * 5
    return result

def process_data(input_list: List[List[int]]) -> List[int]:
    """Processes a list of lists of integers."""
    output = []
    for sublist in input_list:
        output.append(complex_calculation(sublist))
    return output
