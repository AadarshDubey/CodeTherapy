"""Hard task: Retry decorator logic with off-by-one errors."""

import io
import sys
import traceback
from typing import Tuple

from .base_task import BaseTask
from .timeout_util import run_with_timeout


class TaskHard(BaseTask):
    """
    Difficulty: Hard
    Bug: Retry decorator drops the exception instead of re-raising it
         and retries the wrong number of times.
    Tests: No failure, Fail then succeed, Always fail, Test retry count limit.
    """

    name = "retry_decorator_fix"
    difficulty = "hard"
    description = (
        "Fix the @retry_on_exception decorator. The decorator should execute "
        "the function immediately. If it fails, it should retry up to 'max_retries' "
        "adding up to (1 + max_retries) total attempts. If all attempts fail, "
        "it MUST raise the last exception. Currently, it swallows exceptions "
        "and loop bound is incorrect."
    )
    hint = "Count total executed attempts carefully and ensure you use 'raise' to propagate the final failure if retries are exhausted."

    buggy_code = '''\
import time

def retry_on_exception(max_retries=3, delay=0.1):
    """Decorator to retry a function if it raises an exception."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_err = None
            
            # BUG: only runs `max_retries` total times, instead of 1 + max_retries
            for _ in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    time.sleep(delay)
                    
            # BUG: swallows error and implicitly returns None instead of raising last_err
            
        return wrapper
    return decorator
'''

    test_code = '''\
def test_no_failure(retry_on_exception):
    """Decorator should not interfere with successful execution."""
    @retry_on_exception(max_retries=2, delay=0)
    def returns_ok():
        return "SUCCESS"
    
    assert returns_ok() == "SUCCESS", "Failed to return success result."

def test_fail_then_succeed(retry_on_exception):
    """Decorator should return result if it eventually succeeds."""
    attempts = [0]
    
    @retry_on_exception(max_retries=3, delay=0)
    def flaky_func():
        attempts[0] += 1
        if attempts[0] <= 2:
            raise ValueError("Network issue")
        return "FINALLY_SUCCESS"
        
    result = flaky_func()
    assert result == "FINALLY_SUCCESS", f"Expected FINALLY_SUCCESS, got {result}"
    assert attempts[0] == 3, f"Expected 3 attempts, took {attempts[0]}"

def test_always_fail_raises(retry_on_exception):
    """Decorator must re-raise exception if all retries are exhausted."""
    @retry_on_exception(max_retries=2, delay=0)
    def always_fails():
        raise KeyError("I always fail")
        
    try:
        always_fails()
        assert False, "Decorator swallowed the exception and returned silently!"
    except KeyError as e:
        assert str(e) == "'I always fail'", f"Expected specific KeyError, got {e}"
    except Exception as e:
        assert False, f"Expected KeyError, got different exception: {type(e)}"

def test_exact_retry_count(retry_on_exception):
    """Decorator should execute exactly 1 + max_retries times."""
    attempts = [0]
    
    @retry_on_exception(max_retries=2, delay=0)
    def track_attempts():
        attempts[0] += 1
        raise TypeError("Keep failing")
        
    try:
        track_attempts()
    except TypeError:
        pass
        
    assert attempts[0] == 3, f"Expected 3 attempts (1 initial + 2 retries), got {attempts[0]}"
'''

    def run_tests(self, code: str) -> Tuple[int, int, str]:
        """Execute tests against provided code."""
        tests = [
            "test_no_failure",
            "test_fail_then_succeed",
            "test_always_fail_raises",
            "test_exact_retry_count",
        ]
        total = len(tests)
        passed = 0
        output_lines = []

        namespace = {}
        try:
            exec(code.strip(), namespace)
        except Exception:
            return 0, total, f"Code execution error: {traceback.format_exc()}"

        fn = namespace.get("retry_on_exception")
        if fn is None:
            return 0, total, "Error: No 'retry_on_exception' function defined."

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
