"""
sandbox/test_broken_math.py — Ground-truth tests for broken_math.py.

All four tests FAIL against the buggy version.  After TooLoo applies its
three fixes the full suite must be GREEN.

Run directly:
    pytest sandbox/test_broken_math.py -v
"""
from __future__ import annotations

import math
import pytest

# Import the module under test.
# The training-camp runner ensures this path is importable.
from sandbox.broken_math import divide, circle_area, factorial, hypotenuse


# ── BUG-1: divide() — true float division ─────────────────────────────────────

class TestDivide:
    def test_integer_inputs_returns_float(self) -> None:
        """7 / 2 must be 3.5, not 3 (integer division)."""
        assert divide(7, 2) == 3.5

    def test_negative_numerator(self) -> None:
        assert divide(-9, 3) == -3.0

    def test_zero_numerator(self) -> None:
        assert divide(0, 5) == 0.0

    def test_zero_denominator_raises(self) -> None:
        with pytest.raises(ZeroDivisionError):
            divide(1, 0)


# ── BUG-2: circle_area() — must use math.pi ───────────────────────────────────

class TestCircleArea:
    def test_unit_circle(self) -> None:
        """Area of radius-1 circle must be ≈ 3.14159, not 3.0."""
        assert abs(circle_area(1) - math.pi) < 1e-9

    def test_radius_two(self) -> None:
        assert abs(circle_area(2) - 4 * math.pi) < 1e-9

    def test_zero_radius(self) -> None:
        assert circle_area(0) == 0.0


# ── BUG-3: factorial() — must handle n == 0 ───────────────────────────────────

class TestFactorial:
    def test_zero(self) -> None:
        """factorial(0) must return 1, not raise RecursionError."""
        assert factorial(0) == 1

    def test_one(self) -> None:
        assert factorial(1) == 1

    def test_five(self) -> None:
        assert factorial(5) == 120

    def test_ten(self) -> None:
        assert factorial(10) == 3628800


# ── Regression: hypotenuse() must stay correct ────────────────────────────────

class TestHypotenuse:
    def test_3_4_5_triangle(self) -> None:
        assert abs(hypotenuse(3, 4) - 5.0) < 1e-9

    def test_1_1_triangle(self) -> None:
        assert abs(hypotenuse(1, 1) - math.sqrt(2)) < 1e-9
