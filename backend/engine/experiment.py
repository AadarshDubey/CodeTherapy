"""
Experiment Runner — A/B comparison of agent with and without reflection scoring.

Runs two complete debugging episodes on the same task:
  1. Blind mode (no reflection scoring → flat 0.5 reward)
  2. Reflection mode (full LLM-as-a-judge scoring)

Collects per-step metrics for visualization and comparison.
"""

import uuid
import time
from typing import Dict, Any, List, Optional

from backend.engine.environment import DebugEnvironment
from backend.models.action import DebugAction
from backend.agent import get_agent_action


def _run_single_episode(
    task_name: str,
    use_reflection: bool,
    max_steps: int = 8,
) -> Dict[str, Any]:
    """
    Run one complete debugging episode.

    Args:
        task_name: Name of the task to run.
        use_reflection: Whether to use LLM-as-a-judge reflection scoring.
        max_steps: Maximum number of agent steps.

    Returns:
        Dictionary with episode results and per-step data.
    """
    env = DebugEnvironment(use_reflection=use_reflection)
    obs = env.reset(task_name=task_name)

    buggy_code = obs.buggy_code
    test_output = obs.test_output
    initial_code = obs.buggy_code

    steps_data: List[Dict[str, Any]] = []
    history_strs: List[str] = []
    total_reflection_quality = 0.0
    total_code_correctness = 0.0

    start_time = time.time()

    for step in range(1, max_steps + 1):
        if obs.done:
            break

        # Get agent's action from the LLM
        action_dict = get_agent_action(
            buggy_code=buggy_code,
            test_output=test_output,
            step=step,
            history=history_strs,
        )

        # Execute step
        action = DebugAction(
            edits=action_dict["edits"],
            hypothesis=action_dict["hypothesis"],
            action_description=action_dict["action_description"],
            expected_result=action_dict["expected_result"],
        )

        obs = env.step(action)

        # Extract metrics
        reward = obs.reward or 0.0
        breakdown = obs.reward_breakdown or {}
        code_correctness = breakdown.get("code_correctness", 0.0)
        reflection_quality = breakdown.get("reflection_quality", 0.5)
        sub_scores = breakdown.get("reflection_sub_scores", {})

        total_reflection_quality += reflection_quality
        total_code_correctness += code_correctness

        step_entry = {
            "step": step,
            "tests_passed": obs.tests_passed,
            "tests_total": obs.tests_total,
            "reward": round(reward, 4),
            "code_correctness": round(code_correctness, 4),
            "reflection_quality": round(reflection_quality, 4),
            "hypothesis": action_dict["hypothesis"][:300],
            "action_description": action_dict["action_description"][:300],
            "expected_result": action_dict["expected_result"][:300],
            "reflection_sub_scores": sub_scores,
            "done": obs.done,
            "error": obs.last_action_error,
        }
        steps_data.append(step_entry)

        # Update for next iteration
        buggy_code = obs.buggy_code
        test_output = obs.test_output
        history_strs.append(
            f"Step {step}: {action_dict['hypothesis'][:80]} -> reward {reward:+.2f}"
        )

        if obs.done:
            break

    elapsed = round(time.time() - start_time, 2)
    steps_taken = len(steps_data)
    all_pass = obs.tests_passed == obs.tests_total and obs.tests_total > 0

    return {
        "mode": "reflection" if use_reflection else "blind",
        "task_name": task_name,
        "success": all_pass,
        "steps_taken": steps_taken,
        "max_steps": max_steps,
        "final_tests_passed": obs.tests_passed,
        "final_tests_total": obs.tests_total,
        "avg_reflection_quality": round(
            total_reflection_quality / max(steps_taken, 1), 4
        ),
        "avg_code_correctness": round(
            total_code_correctness / max(steps_taken, 1), 4
        ),
        "elapsed_seconds": elapsed,
        "steps": steps_data,
        "initial_code": initial_code,
        "final_code": obs.buggy_code,
    }


def run_experiment(task_name: str) -> Dict[str, Any]:
    """
    Run a full A/B experiment: blind mode vs reflection mode.

    Args:
        task_name: Name of the task to run both episodes on.

    Returns:
        Dictionary with both episode results and comparison metrics.
    """
    experiment_id = str(uuid.uuid4())[:8]

    # Run blind mode first (no reflection scoring)
    blind_result = _run_single_episode(
        task_name=task_name,
        use_reflection=False,
    )

    # Run reflection mode (full system)
    reflection_result = _run_single_episode(
        task_name=task_name,
        use_reflection=True,
    )

    # Compute comparison metrics
    comparison = {
        "success_rate": {
            "blind": 1.0 if blind_result["success"] else 0.0,
            "reflection": 1.0 if reflection_result["success"] else 0.0,
        },
        "steps_taken": {
            "blind": blind_result["steps_taken"],
            "reflection": reflection_result["steps_taken"],
        },
        "avg_fix_quality": {
            "blind": blind_result["avg_code_correctness"],
            "reflection": reflection_result["avg_code_correctness"],
        },
        "avg_reflection_quality": {
            "blind": blind_result["avg_reflection_quality"],
            "reflection": reflection_result["avg_reflection_quality"],
        },
        "final_tests_passed": {
            "blind": blind_result["final_tests_passed"],
            "reflection": reflection_result["final_tests_passed"],
        },
        "tests_total": blind_result["final_tests_total"],
    }

    return {
        "experiment_id": experiment_id,
        "task_name": task_name,
        "blind": blind_result,
        "reflection": reflection_result,
        "comparison": comparison,
    }
