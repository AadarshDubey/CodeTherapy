"""
Inference Script — Reflection Debug Agent
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    LOCAL_IMAGE_NAME The name of the local image to use for the environment if you are using from_docker_image()
                     method

- Defaults are set only for API_BASE_URL and MODEL_NAME
    (and should reflect your active inference setup):
    API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

- The inference script must be named `inference.py` and placed in the root directory of the project
- Participants must use OpenAI Client for all LLM calls using above variables

STDOUT FORMAT
- The script must emit exactly three line types to stdout, in this order:

    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>

  Rules:
    - One [START] line at episode begin.
    - One [STEP] line per step, immediately after env.step() returns.
    - One [END] line after env.close(), always emitted (even on exception).
    - reward and rewards are formatted to 2 decimal places.
    - done and success are lowercase booleans: true or false.
    - error is the raw last_action_error string, or null if none.
    - All fields on a single line with no newlines within a line.
"""

import asyncio
import json
import os
import textwrap
from typing import List, Optional

from openai import OpenAI

# Load .env for local development only (does NOT override existing env vars)
from dotenv import load_dotenv
load_dotenv(override=False)

# --- Environment Client Import ---
# When running with from_docker_image(), the OpenEnv framework generates
# a typed client. For direct HTTP mode, we use httpx.
import httpx

# --- Configuration ---
IMAGE_NAME = os.getenv("IMAGE_NAME")
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
BENCHMARK = "reflection_debug_agent"
MAX_STEPS = 8
TEMPERATURE = 0.7
MAX_TOKENS = 2048

# Task list to iterate through
TASKS = ["api_json_fix", "csv_processor_fix", "retry_decorator_fix"]

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert software engineer debugging code.
    You will be given buggy code and test results.
    
    You must respond with a JSON object containing exactly these fields:
    {
        "hypothesis": "Why the bug exists — reference specific code constructs, variable names, or logic errors.",
        "action_description": "What you will change and why — describe the concrete modification.",
        "expected_result": "What you expect after the fix — which tests should now pass and why.",
        "edits": [{"search": "old code...", "replace": "new code..."}]
    }
    
    IMPORTANT:
    - "edits" must be a list of objects, each containing a "search" and "replace" string.
    - "search" MUST be an EXACT match of a block of code, including all spaces and indentation.
    - "replace" is the exact string to substitute it with.
    - INDENTATION MATTERS: Your "replace" string must include the exact leading spaces/tabs required for proper Python indentation!
    - To insert code, make "search" match the surrounding lines and include them in "replace".
    - Be specific in your hypothesis.
    - Respond ONLY with the JSON object, no other text.
""")


# --- Logging Functions (EXACTLY matching required format) ---

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Clamp reward to strictly (0, 1)
    clamped = min(max(reward, 0.01), 0.99)
    print(
        f"[STEP] step={step} action={action} reward={clamped:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    # Clamp all values to strictly (0, 1)
    clamped_score = min(max(score, 0.01), 0.99)
    clamped_rewards = [min(max(r, 0.01), 0.99) for r in rewards]
    rewards_str = ",".join(f"{r:.2f}" for r in clamped_rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={clamped_score:.3f} rewards={rewards_str}",
        flush=True,
    )


# --- LLM Interaction ---

def build_user_prompt(buggy_code: str, test_output: str, step: int, history: List[str]) -> str:
    history_block = "\n".join(history[-4:]) if history else "None"
    return textwrap.dedent(f"""\
        Step: {step}
        
        Current Code:
        ```python
        {buggy_code}
        ```
        
        Test Results:
        {test_output}
        
        Previous attempts:
        {history_block}
        
        Analyze the bug, fix the code, and provide your structured reflection as JSON.
    """)


def get_model_response(client: OpenAI, buggy_code: str, test_output: str, step: int, history: List[str]) -> dict:
    """Call the LLM and parse its JSON response."""
    user_prompt = build_user_prompt(buggy_code, test_output, step, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()

        # Extract JSON from the response (handle markdown code blocks)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(text)
        return {
            "edits": parsed.get("edits", []),
            "hypothesis": parsed.get("hypothesis", "No hypothesis provided"),
            "action_description": parsed.get("action_description", "No action described"),
            "expected_result": parsed.get("expected_result", "No expected result"),
        }
    except json.JSONDecodeError as e:
        print(f"[DEBUG] JSON parse failed: {e}", flush=True)
        return {
            "edits": [],
            "hypothesis": "Failed to parse LLM response",
            "action_description": "No changes made due to parse error",
            "expected_result": "No improvement expected",
        }
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return {
            "edits": [],
            "hypothesis": f"LLM call failed: {exc}",
            "action_description": "No changes possible",
            "expected_result": "No improvement expected",
        }


# --- Environment Interaction (HTTP-based) ---

class DebugEnvClient:
    """Simple HTTP client for the debug environment."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=120.0)
        self.session_id = None

    def reset(self, task_name: str) -> dict:
        """Reset the environment for a new task."""
        resp = self.client.post(
            f"{self.base_url}/reset",
            json={"task_name": task_name, "session_id": self.session_id},
        )
        resp.raise_for_status()
        data = resp.json()
        self.session_id = data.get("session_id")
        return data

    def step(self, action: dict) -> dict:
        """Take a step in the environment."""
        action["session_id"] = self.session_id
        resp = self.client.post(f"{self.base_url}/step", json=action)
        resp.raise_for_status()
        return resp.json()

    def state(self) -> dict:
        """Get current state."""
        resp = self.client.get(
            f"{self.base_url}/state",
            params={"session_id": self.session_id or ""},
        )
        resp.raise_for_status()
        return resp.json()

    def close(self):
        """Close the HTTP client."""
        self.client.close()


def run_task(client: OpenAI, env: DebugEnvClient, task_name: str) -> tuple:
    """Run a single task episode. Returns (success, steps, score, rewards)."""
    rewards: List[float] = []
    steps_taken = 0
    history: List[str] = []

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset environment
        reset_data = env.reset(task_name)
        obs = reset_data["observation"]
        buggy_code = obs["buggy_code"]
        test_output = obs["test_output"]

        for step in range(1, MAX_STEPS + 1):
            if obs.get("done", False):
                break

            # Get LLM's fix + reflection
            response = get_model_response(client, buggy_code, test_output, step, history)

            # Take a step
            step_data = env.step({
                "edits": response["edits"],
                "hypothesis": response["hypothesis"],
                "action_description": response["action_description"],
                "expected_result": response["expected_result"],
            })

            obs = step_data["observation"]
            reward = step_data.get("reward", 0.0) or 0.0
            reward = min(max(reward, 0.01), 0.99)
            done = step_data.get("done", False)
            error = obs.get("last_action_error")

            rewards.append(reward)
            steps_taken = step
            buggy_code = obs["buggy_code"]
            test_output = obs["test_output"]

            # Format action string for log (abbreviated)
            action_str = f"fix({response['hypothesis'][:50]})"

            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            history.append(
                f"Step {step}: {response['hypothesis'][:80]} -> reward {reward:+.2f}"
            )

            if done:
                break

        # Compute final score
        score = sum(rewards) / len(rewards) if rewards else 0.01
        score = min(max(score, 0.01), 0.99)
        success = score >= 0.5

        return success, steps_taken, score, rewards

    except Exception as exc:
        print(f"[DEBUG] Task {task_name} failed: {exc}", flush=True)
        return False, steps_taken, 0.01, rewards


def main() -> None:
    """Run inference across all tasks."""
    print(f"[DEBUG] Initializing OpenAI client...", flush=True)
    print(f"[DEBUG] API_BASE_URL={API_BASE_URL}", flush=True)
    print(f"[DEBUG] API_KEY={'set (' + API_KEY[:8] + '...)' if API_KEY else 'NOT SET'}", flush=True)
    print(f"[DEBUG] MODEL_NAME={MODEL_NAME}", flush=True)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # Warmup: make a guaranteed LLM call BEFORE any environment interaction
    # This ensures at least one API call goes through the proxy
    try:
        print("[DEBUG] Making warmup LLM call...", flush=True)
        warmup = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": "Say OK"}],
            max_tokens=5,
        )
        print(f"[DEBUG] Warmup LLM call succeeded: {warmup.choices[0].message.content}", flush=True)
    except Exception as exc:
        print(f"[DEBUG] Warmup LLM call FAILED: {exc}", flush=True)

    # Connect to environment
    env_url = os.getenv("ENV_URL", "http://localhost:7860")
    print(f"[DEBUG] ENV_URL={env_url}", flush=True)
    env = DebugEnvClient(env_url)

    all_success = True

    try:
        for task_name in TASKS:
            success, steps, score, rewards = run_task(client, env, task_name)
            log_end(success=success, steps=steps, score=score, rewards=rewards)

            if not success:
                all_success = False

            print(f"[DEBUG] Task {task_name}: score={score:.3f}, success={success}", flush=True)

    finally:
        env.close()

    exit_code = 0 if all_success else 1
    print(f"[DEBUG] All tasks complete. Overall success: {all_success}", flush=True)


if __name__ == "__main__":
    main()
