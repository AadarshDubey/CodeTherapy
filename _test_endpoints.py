"""Quick test: verify all 3 tasks' /reset work without hanging."""
import httpx
import time

client = httpx.Client(timeout=30.0)

tasks = ["fizzbuzz_fix", "binary_search_fix", "linked_list_fix"]

for task in tasks:
    print(f"\n=== Testing {task} ===")
    start = time.time()
    try:
        r = client.post("http://localhost:7860/reset", json={"task_name": task})
        data = r.json()
        elapsed = time.time() - start
        obs = data["observation"]
        print(f"  Time: {elapsed:.1f}s")
        print(f"  Tests: {obs['tests_passed']}/{obs['tests_total']}")
        print(f"  Output: {obs['test_output'][:200]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  FAILED after {elapsed:.1f}s: {e}")

print("\n=== All tasks responded! ===")
