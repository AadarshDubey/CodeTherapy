"""Hard task: Rate limiter with sliding window, burst control, and priority bugs."""

import io
import sys
import traceback
from typing import Tuple

from .base_task import BaseTask
from .timeout_util import run_with_timeout


class TaskHard(BaseTask):
    """
    Difficulty: Hard
    Bug: Rate limiter has multiple interacting bugs across priority handling,
         cooldown logic (wrong duration + boundary error), and state cleanup.
         Fixing one bug often reveals another or breaks a previously passing test.
    Tests: 7 tests covering normal limits, burst, priority bypass, cooldown,
           window sliding, concurrent users, and edge cases.
    """

    name = "retry_decorator_fix"
    difficulty = "hard"
    description = (
        "Fix the RateLimiter class. It implements a sliding-window rate limiter "
        "that tracks requests per user. Features: max N requests per window, "
        "priority users get 2x limit, cooldown period after limit hit, "
        "and old timestamps are cleaned up. Currently has multiple interacting "
        "bugs in window calculation, priority handling, cooldown logic, "
        "and timestamp cleanup."
    )
    hint = "Trace through the timestamp list for each user across multiple calls. Pay attention to how time flows and how the window slides."

    buggy_code = '''\
import time

class RateLimiter:
    def __init__(self, max_requests: int = 5, window_seconds: float = 10.0,
                 cooldown_seconds: float = 5.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.requests = {}      # user_id -> list of timestamps
        self.cooldowns = {}     # user_id -> cooldown_end_time
        self.priority_users = set()

    def add_priority_user(self, user_id: str):
        """Mark user as priority. Priority users get 2x the request limit."""
        self.priority_users.add(user_id)

    def allow_request(self, user_id: str, current_time: float = None):
        """Check if a request is allowed. Returns (allowed: bool, remaining: int)."""
        if current_time is None:
            current_time = time.time()

        # Check cooldown
        if user_id in self.cooldowns:
            if current_time > self.cooldowns[user_id]:
                del self.cooldowns[user_id]
            else:
                return False, 0

        # Initialize user if new
        if user_id not in self.requests:
            self.requests[user_id] = []

        # Clean up old timestamps outside the window
        cutoff = current_time - self.window_seconds
        self.requests[user_id] = [
            t for t in self.requests[user_id] if t > cutoff
        ]

        # Determine effective limit
        limit = self.max_requests
        if user_id in self.priority_users:
            limit = self.max_requests + 1

        current_count = len(self.requests[user_id])

        if current_count >= limit:
            # Rate limited — enter cooldown
            self.cooldowns[user_id] = current_time + self.window_seconds
            return False, 0

        # Allow request
        self.requests[user_id].append(current_time)
        remaining = limit - current_count - 1
        return True, remaining

    def get_usage(self, user_id: str, current_time: float = None):
        """Return dict with current usage stats for a user."""
        if current_time is None:
            current_time = time.time()

        if user_id not in self.requests:
            limit = self.max_requests * 2 if user_id in self.priority_users else self.max_requests
            return {"used": 0, "limit": limit, "remaining": limit}

        cutoff = current_time - self.window_seconds
        active = [t for t in self.requests[user_id] if t > cutoff]
        limit = self.max_requests * 2 if user_id in self.priority_users else self.max_requests
        used = len(active)
        return {"used": used, "limit": limit, "remaining": limit - used}
'''

    test_code = '''\
def test_basic_allow_and_deny(RateLimiter):
    """Basic rate limiting: allow up to max, then deny."""
    rl = RateLimiter(max_requests=3, window_seconds=10.0, cooldown_seconds=2.0)
    t = 100.0
    results = []
    for i in range(5):
        allowed, remaining = rl.allow_request("user1", t + i * 0.1)
        results.append(allowed)
    assert results == [True, True, True, False, False], f"Expected [T,T,T,F,F], got {results}"

def test_window_sliding(RateLimiter):
    """After window passes, old requests should expire and new ones allowed."""
    rl = RateLimiter(max_requests=2, window_seconds=5.0, cooldown_seconds=1.0)
    # Use up limit
    rl.allow_request("user1", 100.0)
    rl.allow_request("user1", 101.0)
    allowed, _ = rl.allow_request("user1", 102.0)
    assert allowed is False, "Should be denied (limit reached)"
    # Wait for cooldown to expire
    # Wait for window to pass (old requests expire)
    allowed, remaining = rl.allow_request("user1", 108.0)
    assert allowed is True, "Should be allowed after window expires"
    assert remaining >= 0, f"Remaining should be non-negative, got {remaining}"

def test_priority_double_limit(RateLimiter):
    """Priority users should get 2x the request limit."""
    rl = RateLimiter(max_requests=3, window_seconds=10.0, cooldown_seconds=2.0)
    rl.add_priority_user("vip")
    t = 100.0
    results = []
    for i in range(7):
        allowed, _ = rl.allow_request("vip", t + i * 0.1)
        results.append(allowed)
    # 2x limit = 6 allowed, 7th denied
    assert results == [True, True, True, True, True, True, False], f"Expected 6 allowed then denied, got {results}"

def test_cooldown_correct_duration(RateLimiter):
    """After hitting limit, cooldown should last cooldown_seconds, not window_seconds."""
    rl = RateLimiter(max_requests=2, window_seconds=2.0, cooldown_seconds=5.0)
    rl.allow_request("user1", 100.0)
    rl.allow_request("user1", 100.1)
    rl.allow_request("user1", 100.2)  # denied, enters cooldown

    # At t=103.0: past window_seconds(2) but within cooldown_seconds(5)
    # If cooldown wrongly uses window_seconds: ends at 102.2 -> allowed (BUG)
    # Correct cooldown: ends at 105.2 -> still denied
    allowed, _ = rl.allow_request("user1", 103.0)
    assert allowed is False, "Should still be in cooldown (cooldown=5s, not window=2s)"

    # After full cooldown expires (past 100.2 + 5.0 = 105.2)
    allowed, _ = rl.allow_request("user1", 106.0)
    assert allowed is True, "Should be allowed after cooldown expires"

def test_cooldown_boundary(RateLimiter):
    """At exactly cooldown expiry time, request should be allowed."""
    rl = RateLimiter(max_requests=1, window_seconds=2.0, cooldown_seconds=5.0)
    rl.allow_request("user1", 100.0)
    rl.allow_request("user1", 100.1)  # denied, enters cooldown at 100.1

    # Exactly at cooldown end (100.1 + 5.0 = 105.1)
    allowed, _ = rl.allow_request("user1", 105.1)
    assert allowed is True, f"Should be allowed at exact cooldown expiry"

def test_independent_users(RateLimiter):
    """Different users should have independent limits."""
    rl = RateLimiter(max_requests=2, window_seconds=10.0, cooldown_seconds=2.0)
    rl.allow_request("alice", 100.0)
    rl.allow_request("alice", 100.1)
    # Alice is maxed out
    allowed_alice, _ = rl.allow_request("alice", 100.2)
    assert allowed_alice is False, "Alice should be denied"
    # Bob should still be fine
    allowed_bob, remaining = rl.allow_request("bob", 100.2)
    assert allowed_bob is True, "Bob should be allowed"
    assert remaining == 1, f"Bob should have 1 remaining, got {remaining}"

def test_usage_non_negative(RateLimiter):
    """get_usage remaining should never be negative."""
    rl = RateLimiter(max_requests=1, window_seconds=10.0, cooldown_seconds=2.0)
    rl.allow_request("user1", 100.0)
    usage = rl.get_usage("user1", 100.5)
    assert usage["remaining"] >= 0, f"Remaining should be non-negative, got {usage['remaining']}"
    assert usage["used"] == 1, f"Used should be 1, got {usage['used']}"
'''

    def run_tests(self, code: str) -> Tuple[int, int, str]:
        """Execute tests against provided code."""
        tests = [
            "test_basic_allow_and_deny",
            "test_window_sliding",
            "test_priority_double_limit",
            "test_cooldown_correct_duration",
            "test_cooldown_boundary",
            "test_independent_users",
            "test_usage_non_negative",
        ]
        total = len(tests)
        passed = 0
        output_lines = []

        namespace = {}
        try:
            exec(code.strip(), namespace)
        except Exception:
            return 0, total, f"Code execution error: {traceback.format_exc()}"

        cls = namespace.get("RateLimiter")
        if cls is None:
            return 0, total, "Error: No 'RateLimiter' class defined."

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
