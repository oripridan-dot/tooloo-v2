import pytest
from pathlib import Path

# Assume the component code is in a file named 'full_cycle_si_e56762ac.py' for testing purposes
# In a real scenario, this would be imported from the actual component path.
# For this isolated test, we'll simulate the import.

# Mocking the component function for isolated testing if it were a separate file
def calculate_discount(price: float, discount_percentage: float) -> float:
    if not (0 <= discount_percentage <= 100):
        raise ValueError("Discount percentage must be between 0 and 100.")
    discount_amount = price * (discount_percentage / 100)
    return price - discount_amount

def process_order(order_details: dict) -> dict:
    product_price = order_details.get("price", 0.0)
    discount = order_details.get("discount", 0.0)

    try:
        final_price = calculate_discount(product_price, discount)
        order_details["final_price"] = final_price
        order_details["status"] = "processed"
    except ValueError as e:
        order_details["error"] = str(e)
        order_details["status"] = "failed"

    return order_details


# --- Tests ---

def test_successful_discount_calculation():
    order = {"item": "Keyboard", "price": 75.00, "discount": 10.0}
    result = process_order(order)
    assert result["final_price"] == 67.50
    assert result["status"] == "processed"

def test_invalid_discount_percentage_above_100():
    order = {"item": "Monitor", "price": 300.00, "discount": 110.0}
    result = process_order(order)
    assert "Discount percentage must be between 0 and 100." in result.get("error", "")
    assert result["status"] == "failed"

def test_invalid_discount_percentage_below_0():
    order = {"item": "Webcam", "price": 50.00, "discount": -10.0}
    result = process_order(order)
    assert "Discount percentage must be between 0 and 100." in result.get("error", "")
    assert result["status"] == "failed"

def test_zero_discount():
    order = {"item": "Desk Lamp", "price": 30.00, "discount": 0.0}
    result = process_order(order)
    assert result["final_price"] == 30.00
    assert result["status"] == "processed"

def test_full_discount():
    order = {"item": "Mousepad", "price": 15.00, "discount": 100.0}
    result = process_order(order)
    assert result["final_price"] == 0.00
    assert result["status"] == "processed"

def test_order_with_no_discount_key():
    order = {"item": "USB Drive", "price": 20.00}
    result = process_order(order)
    assert result["final_price"] == 20.00 # Should default to 0 discount if not present
    assert result["status"] == "processed"

