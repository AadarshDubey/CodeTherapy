"""Easy task: Stateful shopping cart with discount logic bugs."""

import io
import sys
import traceback
from typing import Tuple

from .base_task import BaseTask
from .timeout_util import run_with_timeout


class TaskEasy(BaseTask):
    """
    Difficulty: Easy
    Bug: Shopping cart has multiple interacting bugs:
         1) add_item doesn't validate quantity (allows negative)
         2) apply_discount mutates when discount > 100%
         3) get_total doesn't handle empty cart
         4) remove_item fails silently on non-existent items
    Tests: 5 tests covering normal ops + edge cases
    """

    name = "api_json_fix"
    difficulty = "easy"
    description = (
        "Fix the ShoppingCart class. It should support adding items with "
        "name/price/quantity, removing items, applying percentage discounts, "
        "and computing totals. Currently it has multiple bugs: negative quantities "
        "are allowed, discounts over 100% create negative prices, empty cart "
        "total crashes, and removing non-existent items raises KeyError."
    )
    hint = "Each method has at least one bug. Validate inputs and handle edge cases."

    buggy_code = '''\
class ShoppingCart:
    def __init__(self):
        self.items = {}

    def add_item(self, name: str, price: float, quantity: int = 1):
        """Add item to cart. Quantity must be positive."""
        if name in self.items:
            self.items[name]["quantity"] += quantity
        else:
            self.items[name] = {"price": price, "quantity": quantity}

    def remove_item(self, name: str):
        """Remove item from cart. Should return False if item not found."""
        del self.items[name]
        return True

    def apply_discount(self, name: str, percent: float):
        """Apply percentage discount to an item. Discount must be 0-100."""
        if name in self.items:
            self.items[name]["price"] *= (1 - percent / 100)

    def get_total(self):
        """Return total cost of all items in cart."""
        total = 0
        for item in self.items.values():
            total += item["price"] * item["quantity"]
        return total
'''

    test_code = '''\
def test_add_and_total(ShoppingCart):
    """Basic add and total should work."""
    cart = ShoppingCart()
    cart.add_item("apple", 1.50, 3)
    cart.add_item("bread", 2.00, 1)
    assert cart.get_total() == 6.50, f"Expected 6.50, got {cart.get_total()}"

def test_negative_quantity_rejected(ShoppingCart):
    """Adding negative quantity should raise ValueError."""
    cart = ShoppingCart()
    try:
        cart.add_item("apple", 1.50, -5)
        assert False, "Should have raised ValueError for negative quantity"
    except ValueError:
        pass

def test_remove_nonexistent(ShoppingCart):
    """Removing item not in cart should return False, not crash."""
    cart = ShoppingCart()
    result = cart.remove_item("ghost_item")
    assert result is False, f"Expected False for non-existent item, got {result}"

def test_discount_bounds(ShoppingCart):
    """Discount over 100% should raise ValueError."""
    cart = ShoppingCart()
    cart.add_item("laptop", 1000.0)
    try:
        cart.apply_discount("laptop", 150)
        assert False, "Should have raised ValueError for discount > 100"
    except ValueError:
        pass

def test_empty_cart_total(ShoppingCart):
    """Empty cart total should return 0.0."""
    cart = ShoppingCart()
    assert cart.get_total() == 0.0, f"Expected 0.0, got {cart.get_total()}"
'''

    def run_tests(self, code: str) -> Tuple[int, int, str]:
        """Execute tests against provided code."""
        tests = [
            "test_add_and_total",
            "test_negative_quantity_rejected",
            "test_remove_nonexistent",
            "test_discount_bounds",
            "test_empty_cart_total",
        ]
        total = len(tests)
        passed = 0
        output_lines = []

        namespace = {}
        try:
            exec(code.strip(), namespace)
        except Exception:
            return 0, total, f"Code execution error: {traceback.format_exc()}"

        cls = namespace.get("ShoppingCart")
        if cls is None:
            return 0, total, "Error: No 'ShoppingCart' class defined."

        test_namespace = {}
        try:
            exec(self.test_code, test_namespace)
        except Exception:
            return 0, total, f"Test code error: {traceback.format_exc()}"

        for test_name in tests:
            test_fn = test_namespace.get(test_name)
            if test_fn is None:
                continue

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                _, timeout_err = run_with_timeout(test_fn, (cls,), timeout_s=5.0)
                if timeout_err:
                    output_lines.append(f"  ERROR {test_name}: {timeout_err}")
                else:
                    passed += 1
                    output_lines.append(f"  PASS {test_name}")
            except AssertionError as e:
                output_lines.append(f"  FAIL {test_name}: {e}")
            except Exception as e:
                output_lines.append(f"  ERROR {test_name}: {e}")
            finally:
                sys.stdout = old_stdout

        summary = f"Tests: {passed}/{total} passed\n" + "\n".join(output_lines)
        return passed, total, summary

    def grade(self, tests_passed: int, tests_total: int) -> float:
        if tests_total == 0:
            return 0.0
        return round(tests_passed / tests_total, 2)
