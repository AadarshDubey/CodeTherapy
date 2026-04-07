"""Medium task: Edge cases in CSV data processing."""

import io
import sys
import traceback
from typing import Tuple

from .base_task import BaseTask
from .timeout_util import run_with_timeout


class TaskMedium(BaseTask):
    """
    Difficulty: Medium
    Bug: CSV processor fails to handle empty rows and missing data fields.
    Tests: Clean data, missing amounts, empty records.
    """

    name = "csv_processor_fix"
    difficulty = "medium"
    description = (
        "Fix the process_sales_data function. It reads a raw CSV string containing "
        "store_id and amount, and aggregates total sales. "
        "It must handle empty lines gracefully and treat empty 'amount' strings as 0.0. "
        "Currently, it crashes on empty amounts (ValueError) and missing store_id."
    )
    hint = "Check each row to ensure 'store_id' and 'amount' actually contain valid data before processing them."

    buggy_code = '''\
def process_sales_data(csv_data: str):
    """Parse CSV string and return total sales per store as a dict."""
    sales = {}
    
    # BUG: Doesn't handle empty lines gracefully
    for line in csv_data.strip().split('\\n'):
        if line.startswith("store_id"):
            continue
            
        parts = line.split(',')
        store = parts[0]
        
        # BUG: Crashes with ValueError if amount is ""
        amount = float(parts[1])
        
        if store not in sales:
            sales[store] = 0.0
            
        sales[store] += amount
        
    return sales
'''

    test_code = '''\
def test_clean_data(process_sales_data):
    """Processor should aggregate clean data correctly."""
    csv_data = "store_id,amount\\nA,10.5\\nB,20.0\\nA,5.5"
    result = process_sales_data(csv_data)
    assert result == {"A": 16.0, "B": 20.0}, f"Expected {{'A': 16.0, 'B': 20.0}}, got {result}"

def test_missing_amount(process_sales_data):
    """Processor should treat empty amounts as 0.0 and not crash."""
    csv_data = "store_id,amount\\nA,10.0\\nB,\\nA,5.0"
    result = process_sales_data(csv_data)
    assert result == {"A": 15.0, "B": 0.0}, f"Expected {{'A': 15.0, 'B': 0.0}}, got {result}"

def test_empty_rows(process_sales_data):
    """Processor should skip completely empty rows."""
    csv_data = "store_id,amount\\nA,10.0\\n\\nB,20.0"
    result = process_sales_data(csv_data)
    assert result == {"A": 10.0, "B": 20.0}, f"Expected {{'A': 10.0, 'B': 20.0}}, got {result}"
'''

    def run_tests(self, code: str) -> Tuple[int, int, str]:
        """Execute binary search tests against provided code."""
        tests = [
            "test_clean_data",
            "test_missing_amount",
            "test_empty_rows",
        ]
        total = len(tests)
        passed = 0
        output_lines = []

        namespace = {}
        try:
            exec(code.strip(), namespace)
        except Exception:
            return 0, total, f"Code execution error: {traceback.format_exc()}"

        fn = namespace.get("process_sales_data")
        if fn is None:
            return 0, total, "Error: No 'process_sales_data' function defined."

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
                _, timeout_err = run_with_timeout(test_fn, (fn,), timeout_s=5.0)
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
