import pytest

# Assuming the component 'full-cycle-si-71e0054e' is available in the scope
# For testing purposes, we'll use a placeholder implementation
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)

def fibonacci(n):
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    def add(self, x, y):
        return x + y

    def subtract(self, x, y):
        return x - y

    def multiply(self, x, y):
        return x * y

    def divide(self, x, y):
        if y == 0:
            raise ValueError("Division by zero")
        return x / y


# Test cases for factorial
def test_factorial_zero():
    assert factorial(0) == 1

def test_factorial_positive():
    assert factorial(5) == 120

# Test cases for fibonacci
def test_fibonacci_zero():
    assert fibonacci(0) == 0

def test_fibonacci_positive():
    assert fibonacci(10) == 55

# Test cases for Calculator.add
def test_calculator_add():
    calc = Calculator()
    assert calc.add(5, 3) == 8

# Test cases for Calculator.subtract
def test_calculator_subtract():
    calc = Calculator()
    assert calc.subtract(10, 4) == 6

# Test cases for Calculator.multiply
def test_calculator_multiply():
    calc = Calculator()
    assert calc.multiply(6, 7) == 42

# Test cases for Calculator.divide
def test_calculator_divide():
    calc = Calculator()
    assert calc.divide(20, 5) == 4.0

def test_calculator_divide_by_zero():
    calc = Calculator()
    with pytest.raises(ValueError, match="Division by zero"):
        calc.divide(10, 0)
