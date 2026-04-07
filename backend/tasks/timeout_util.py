"""Utility for running functions with a timeout on Windows (using threading)."""

import threading
from typing import Any, Callable, Optional, Tuple


class TimeoutError(Exception):
    """Raised when a function call exceeds the timeout."""
    pass


def run_with_timeout(func: Callable, args: tuple = (), timeout_s: float = 5.0) -> Tuple[Any, Optional[str]]:
    """
    Run a function with a timeout. Works on Windows (uses threading).

    Args:
        func: The function to call.
        args: Arguments to pass to the function.
        timeout_s: Max seconds to wait.

    Returns:
        Tuple of (result, error_string). If the function
        completes in time, error_string is None. If it times out,
        result is None and error_string describes the timeout.
    """
    result = [None]
    error = [None]

    def target():
        try:
            result[0] = func(*args)
        except Exception as e:
            error[0] = e

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=timeout_s)

    if thread.is_alive():
        # Thread is still running — it's stuck in an infinite loop
        # We can't forcibly kill a thread in Python, but since it's
        # a daemon thread it won't block process exit.
        return None, f"Timed out after {timeout_s}s (likely infinite loop)"

    if error[0] is not None:
        raise error[0]

    return result[0], None
