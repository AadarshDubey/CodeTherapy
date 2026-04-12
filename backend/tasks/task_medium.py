"""Medium task: LRU Cache with subtle state management bugs."""

import io
import sys
import traceback
from typing import Tuple

from .base_task import BaseTask
from .timeout_util import run_with_timeout


class TaskMedium(BaseTask):
    """
    Difficulty: Medium
    Bug: LRU Cache has multiple subtle interacting bugs:
         1) put() doesn't move existing key to front (stale ordering)
         2) Eviction removes newest instead of oldest (wrong end)
         3) get() doesn't update access order (no LRU tracking)
         4) capacity check is off-by-one (evicts too early)
         5) delete returns wrong value on miss
    Tests: 6 tests covering insertion, eviction order, access patterns, edge cases
    """

    name = "csv_processor_fix"
    difficulty = "medium"
    description = (
        "Fix the LRUCache class. It should store key-value pairs up to a maximum "
        "capacity. When the cache is full and a new key is added, the LEAST recently "
        "used key should be evicted. Both get() and put() should count as 'using' a key. "
        "Currently it has multiple bugs: eviction removes wrong item, get() doesn't "
        "update recency, put() on existing key doesn't refresh order, and capacity "
        "check has off-by-one error."
    )
    hint = "Trace through the order list carefully for each operation. The order list tracks recency — most recent should be at the end."

    buggy_code = '''\
class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}
        self.order = []  # tracks access order: oldest at index 0, newest at end

    def get(self, key: str):
        """Return value if key exists, else return -1. Should update access order."""
        if key in self.cache:
            return self.cache[key]
        return -1

    def put(self, key: str, value):
        """Add or update key-value pair. Evict LRU if over capacity."""
        if key in self.cache:
            self.cache[key] = value
            return

        if len(self.cache) > self.capacity:
            oldest = self.order.pop()
            del self.cache[oldest]

        self.cache[key] = value
        self.order.append(key)

    def delete(self, key: str):
        """Remove key from cache. Return True if found, False if not."""
        if key in self.cache:
            del self.cache[key]
            self.order.remove(key)
            return True
'''

    test_code = '''\
def test_basic_put_get(LRUCache):
    """Basic put and get should work."""
    cache = LRUCache(3)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == 1, f"Expected 1, got {cache.get('a')}"
    assert cache.get("b") == 2, f"Expected 2, got {cache.get('b')}"
    assert cache.get("c") == -1, "Expected -1 for missing key"

def test_eviction_removes_lru(LRUCache):
    """When full, adding new key should evict the LEAST recently used."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)  # should evict "a" (oldest)
    assert cache.get("a") == -1, "Expected 'a' to be evicted"
    assert cache.get("b") == 2, f"Expected 2, got {cache.get('b')}"
    assert cache.get("c") == 3, f"Expected 3, got {cache.get('c')}"

def test_get_updates_recency(LRUCache):
    """Calling get() should make that key most recently used."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")       # "a" is now most recent, "b" is LRU
    cache.put("c", 3)    # should evict "b", NOT "a"
    assert cache.get("a") == 1, "Expected 'a' to survive (was accessed recently)"
    assert cache.get("b") == -1, "Expected 'b' to be evicted (was LRU)"

def test_put_existing_refreshes(LRUCache):
    """Updating existing key should refresh its recency."""
    cache = LRUCache(2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("a", 10)   # update "a" — now "a" is most recent, "b" is LRU
    cache.put("c", 3)    # should evict "b"
    assert cache.get("a") == 10, f"Expected 10, got {cache.get('a')}"
    assert cache.get("b") == -1, "Expected 'b' to be evicted"
    assert cache.get("c") == 3, f"Expected 3, got {cache.get('c')}"

def test_delete_returns_correct(LRUCache):
    """Delete should return True if found, False if not."""
    cache = LRUCache(3)
    cache.put("a", 1)
    assert cache.delete("a") is True, "Expected True for existing key"
    assert cache.delete("z") is False, "Expected False for non-existent key"
    assert cache.get("a") == -1, "Expected -1 after deletion"

def test_capacity_one(LRUCache):
    """Cache with capacity 1 should always hold only the latest item."""
    cache = LRUCache(1)
    cache.put("a", 1)
    cache.put("b", 2)
    assert cache.get("a") == -1, "Expected 'a' evicted in cap-1 cache"
    assert cache.get("b") == 2, f"Expected 2, got {cache.get('b')}"
'''

    def run_tests(self, code: str) -> Tuple[int, int, str]:
        """Execute tests against provided code."""
        tests = [
            "test_basic_put_get",
            "test_eviction_removes_lru",
            "test_get_updates_recency",
            "test_put_existing_refreshes",
            "test_delete_returns_correct",
            "test_capacity_one",
        ]
        total = len(tests)
        passed = 0
        output_lines = []

        namespace = {}
        try:
            exec(code.strip(), namespace)
        except Exception:
            return 0, total, f"Code execution error: {traceback.format_exc()}"

        cls = namespace.get("LRUCache")
        if cls is None:
            return 0, total, "Error: No 'LRUCache' class defined."

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
