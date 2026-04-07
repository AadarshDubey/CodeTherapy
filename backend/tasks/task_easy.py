"""Easy task: JSON parsing bug in API handler."""

import io
import sys
import traceback
from typing import Tuple

from .base_task import BaseTask
from .timeout_util import run_with_timeout


class TaskEasy(BaseTask):
    """
    Difficulty: Easy
    Bug: Mock API fails to parse invalid JSON safely and accesses dict with dot notation.
    Tests: Valid JSON payload, Invalid JSON payload, Missing keys.
    """

    name = "api_json_fix"
    difficulty = "easy"
    description = (
        "Fix the mock API request handler. It receives a JSON string payload "
        "and should return a dictionary. If the payload is invalid JSON, "
        "it should return {'status': 'error', 'message': 'Invalid payload'}. "
        "Otherwise, it should return {'status': 'success', 'user': <username>}. "
        "Currently, it crashes on invalid JSON and uses dot-notation instead of brackets."
    )
    hint = "Handle exceptions when parsing JSON and remember that Python dictionaries require bracket matching for keys, not dot notation like JavaScript."

    buggy_code = '''\
import json

def handle_request(payload: str):
    """Process incoming JSON payload and extract user."""
    # BUG: json.loads crashes if payload is invalid JSON (no try/except)
    data = json.loads(payload)
    
    # BUG: dict does not support dot-notation in Python
    username = data.username
    
    return {"status": "success", "user": username}
'''

    test_code = '''\
import json
def test_valid_json(handle_request):
    """Handler should correctly parse valid JSON."""
    payload = json.dumps({"username": "alice99", "role": "admin"})
    result = handle_request(payload)
    assert result == {"status": "success", "user": "alice99"}, f"Expected success response, got {result}"

def test_invalid_json(handle_request):
    """Handler should catch JSONDecodeError and return error dict."""
    payload = "{invalid: json, string]"
    result = handle_request(payload)
    expected = {"status": "error", "message": "Invalid payload"}
    assert result == expected, f"Expected {expected}, got {result}"

def test_missing_username(handle_request):
    """Valid user parsing test."""
    payload = json.dumps({"username": "bob_builder"})
    result = handle_request(payload)
    assert result == {"status": "success", "user": "bob_builder"}
'''

    def run_tests(self, code: str) -> Tuple[int, int, str]:
        """Execute tests against provided code."""
        tests = [
            "test_valid_json",
            "test_invalid_json",
            "test_missing_username",
        ]
        total = len(tests)
        passed = 0
        output_lines = []

        namespace = {}
        try:
            exec(code.strip(), namespace)
        except Exception:
            return 0, total, f"Code execution error: {traceback.format_exc()}"

        fn = namespace.get("handle_request")
        if fn is None:
            return 0, total, "Error: No 'handle_request' function defined."

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
