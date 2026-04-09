"""
evaluate_baselines.py — Quantitative Evaluation Script

Runs tasks against three baselines:
1. Base LLM (No structured reflection)
2. RL Agent (Outcome-only reward: reflection allowed but not scored)
3. Proposed (RL Agent with Reflection Scoring)
"""

import sys
import os
import json
import textwrap
from typing import List

# Ensure the parent directory is in the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

from backend.engine.environment import DebugEnvironment
from backend.models.action import DebugAction

API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

TASKS = ["api_json_fix", "csv_processor_fix", "retry_decorator_fix"]
MAX_STEPS = 5

def build_no_reflection_prompt() -> str:
    return textwrap.dedent("""\
        You are an expert software engineer.
        You must fix the buggy code based on the test results.
        
        Respond with ONLY a JSON object containing an "edits" list:
        {
            "edits": [{"search": "old code...", "replace": "new code..."}]
        }
        
        IMPORTANT:
        - "search" MUST be an EXACT match of a block of code, including indentation.
        - Respond ONLY with the JSON object.
    """)

def build_proposed_prompt() -> str:
    from backend.agent import SYSTEM_PROMPT
    return SYSTEM_PROMPT

def get_agent_action_sync(client: OpenAI, buggy_code: str, test_output: str, step: int, history: List[str], prompt: str) -> dict:
    history_block = "\n".join(history[-4:]) if history else "None"
    user_prompt = textwrap.dedent(f"""\
        Step: {step}
        Current Code:
        ```python
        {buggy_code}
        ```
        Test Results:
        {test_output}
        Previous attempts:
        {history_block}
        Fix the code.
    """)
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2048,
        )
        text = (completion.choices[0].message.content or "").strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(text)
        return {
            "edits": parsed.get("edits", []),
            "hypothesis": parsed.get("hypothesis", "N/A"),
            "action_description": parsed.get("action_description", "N/A"),
            "expected_result": parsed.get("expected_result", "N/A"),
        }
    except Exception as e:
        return {"edits": [], "hypothesis": "Failed", "action_description": "Failed", "expected_result": "Failed"}

def run_eval(mode: str, task_name: str, client: OpenAI) -> tuple:
    env = DebugEnvironment()
    
    if mode == "outcome_only":
        env.REWARD_WEIGHT_REFLECTION = 0.0
        env.REWARD_WEIGHT_CODE = 1.0
        sys_prompt = build_proposed_prompt()
    elif mode == "no_reflection":
        sys_prompt = build_no_reflection_prompt()
    else:
        # proposed
        sys_prompt = build_proposed_prompt()
        
    obs = env.reset(task_name=task_name)
    buggy_code = obs.buggy_code
    test_output = obs.test_output
    
    history_strs = []
    
    for step in range(1, MAX_STEPS + 1):
        if obs.done:
            break
            
        action_dict = get_agent_action_sync(client, buggy_code, test_output, step, history_strs, sys_prompt)
        
        action = DebugAction(
            edits=action_dict["edits"],
            hypothesis=action_dict["hypothesis"],
            action_description=action_dict["action_description"],
            expected_result=action_dict["expected_result"],
        )
        
        obs = env.step(action)
        reward = obs.reward or 0.0
        
        buggy_code = obs.buggy_code
        test_output = obs.test_output
        history_strs.append(f"Step {step}: success rate {obs.tests_passed}/{obs.tests_total}")
        
    final_success_rate = obs.tests_passed / obs.tests_total if obs.tests_total > 0 else 0
    return final_success_rate, env._state.step_count, env._state.best_score

def main():
    print(f"Using Model: {MODEL_NAME}")
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    modes = ["no_reflection", "outcome_only", "proposed"]
    
    results = {m: {"success": 0, "steps": 0, "score": 0.0} for m in modes}
    total_tasks = len(TASKS)
    
    print("Running baseline evaluations... This will execute real LLM calls.")
    for task in TASKS:
        for mode in modes:
            print(f"Evaluating {task} in {mode} mode...")
            success_rate, steps, score = run_eval(mode, task, client)
            results[mode]["success"] += 1 if success_rate == 1.0 else 0
            results[mode]["steps"] += steps
            results[mode]["score"] += score
            print(f"  -> Success: {success_rate==1.0}, Steps: {steps}, Final Reward: {score:.2f}")
            
    print("\n# Evaluation Report\n")
    print("| Method | Pass Rate | Avg Steps to Converge | Avg Reward |")
    print("|---|---|---|---|")
    for mode in modes:
        pass_rate = (results[mode]["success"] / total_tasks) * 100
        avg_steps = results[mode]["steps"] / total_tasks
        avg_score = results[mode]["score"] / total_tasks
        print(f"| {mode} | {pass_rate:.1f}% | {avg_steps:.1f} | {avg_score:.2f} |")

if __name__ == "__main__":
    main()
