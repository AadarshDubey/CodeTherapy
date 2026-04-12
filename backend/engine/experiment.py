"""
Experiment Runner — A/B comparison of agent with and without reflection scoring.

Runs two complete debugging episodes on the same task:
  1. Blind mode: Single-shot, no history, 1 step max
  2. Reflection mode: Multi-turn conversation with iterative refinement, 8 steps

Collects per-step metrics for visualization and comparison.
Experiment order is randomized to avoid systematic bias.
"""

import uuid
import time
import random
from typing import Dict, Any, List, Optional

from backend.engine.environment import DebugEnvironment
from backend.models.action import DebugAction
from backend.agent import get_agent_action, get_blind_agent_action


def _run_single_episode(
    task_name: str,
    use_reflection: bool,
    max_steps: int = 8,
) -> Dict[str, Any]:
    """Run one complete debugging episode."""
    env = DebugEnvironment(use_reflection=use_reflection)
    obs = env.reset(task_name=task_name)

    buggy_code = obs.buggy_code
    test_output = obs.test_output
    initial_code = obs.buggy_code

    steps_data: List[Dict[str, Any]] = []
    messages = None  # Multi-turn conversation state (reflection agent only)
    total_reflection_quality = 0.0
    total_code_correctness = 0.0

    start_time = time.time()

    for step in range(1, max_steps + 1):
        if obs.done:
            break

        # Get agent's action
        if use_reflection:
            # Multi-turn: pass conversation history
            action_dict, messages = get_agent_action(
                buggy_code=buggy_code,
                test_output=test_output,
                step=step,
                history=[],  # not used — messages handle history
                messages=messages,
                max_steps=max_steps,
            )
        else:
            # Blind: single-turn, no history
            action_dict = get_blind_agent_action(
                buggy_code=buggy_code,
                test_output=test_output,
                step=step,
                history=[],
            )

        # Execute step in environment
        action = DebugAction(
            edits=action_dict["edits"],
            hypothesis=action_dict.get("hypothesis", ""),
            action_description=action_dict.get("action_description", ""),
            expected_result=action_dict.get("expected_result", ""),
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
            "hypothesis": action_dict.get("hypothesis", "")[:300],
            "action_description": action_dict.get("action_description", "")[:300],
            "expected_result": action_dict.get("expected_result", "")[:300],
            "reflection_sub_scores": sub_scores,
            "done": obs.done,
            "error": obs.last_action_error,
        }
        steps_data.append(step_entry)

        # Update for next iteration
        buggy_code = obs.buggy_code
        test_output = obs.test_output

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


def _build_comparison(blind_result: Dict[str, Any], reflection_result: Dict[str, Any]) -> Dict[str, Any]:
    """Build comparison metrics between blind and reflection results."""
    return {
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


def run_experiment(task_name: str) -> Dict[str, Any]:
    """
    Run a full A/B experiment: blind mode vs reflection mode.
    Order is randomized to avoid systematic bias.
    """
    experiment_id = str(uuid.uuid4())[:8]

    run_blind_first = random.choice([True, False])

    if run_blind_first:
        blind_result = _run_single_episode(task_name=task_name, use_reflection=False, max_steps=1)
        reflection_result = _run_single_episode(task_name=task_name, use_reflection=True)
    else:
        reflection_result = _run_single_episode(task_name=task_name, use_reflection=True)
        blind_result = _run_single_episode(task_name=task_name, use_reflection=False, max_steps=1)

    comparison = _build_comparison(blind_result, reflection_result)

    return {
        "experiment_id": experiment_id,
        "task_name": task_name,
        "blind": blind_result,
        "reflection": reflection_result,
        "comparison": comparison,
    }


# ─── Streaming Version (for frontend SSE) ────────────────────────────

def _run_single_episode_stream(
    task_name: str,
    use_reflection: bool,
    max_steps: int = 8,
):
    """
    Generator version of _run_single_episode.
    Yields SSE-friendly dicts after each step.
    """
    mode = "reflection" if use_reflection else "blind"
    env = DebugEnvironment(use_reflection=use_reflection)
    obs = env.reset(task_name=task_name)

    buggy_code = obs.buggy_code
    test_output = obs.test_output
    initial_code = obs.buggy_code

    steps_data: List[Dict[str, Any]] = []
    messages = None  # Multi-turn conversation state
    total_reflection_quality = 0.0
    total_code_correctness = 0.0

    start_time = time.time()

    for step in range(1, max_steps + 1):
        if obs.done:
            break

        # Emit "thinking" event before LLM call
        yield {
            "type": "thinking",
            "mode": mode,
            "step": step,
            "max_steps": max_steps,
        }

        # Get agent's action
        if use_reflection:
            action_dict, messages = get_agent_action(
                buggy_code=buggy_code,
                test_output=test_output,
                step=step,
                history=[],
                messages=messages,
                max_steps=max_steps,
            )
        else:
            action_dict = get_blind_agent_action(
                buggy_code=buggy_code,
                test_output=test_output,
                step=step,
                history=[],
            )

        # Execute step in environment
        action = DebugAction(
            edits=action_dict["edits"],
            hypothesis=action_dict.get("hypothesis", ""),
            action_description=action_dict.get("action_description", ""),
            expected_result=action_dict.get("expected_result", ""),
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
            "hypothesis": action_dict.get("hypothesis", "")[:300],
            "action_description": action_dict.get("action_description", "")[:300],
            "expected_result": action_dict.get("expected_result", "")[:300],
            "reflection_sub_scores": sub_scores,
            "done": obs.done,
            "error": obs.last_action_error,
        }
        steps_data.append(step_entry)

        # Emit "step" event
        yield {
            "type": "step",
            "mode": mode,
            "data": step_entry,
        }

        # Update for next iteration
        buggy_code = obs.buggy_code
        test_output = obs.test_output

        if obs.done:
            break

    elapsed = round(time.time() - start_time, 2)
    steps_taken = len(steps_data)
    all_pass = obs.tests_passed == obs.tests_total and obs.tests_total > 0

    result = {
        "mode": mode,
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

    # Emit phase_end
    yield {
        "type": "phase_end",
        "mode": mode,
        "result": result,
    }

    return result


def run_experiment_stream(task_name: str):
    """
    Generator that yields SSE events for the full A/B experiment.
    Order is randomized to avoid systematic bias.
    """
    experiment_id = str(uuid.uuid4())[:8]

    run_blind_first = random.choice([True, False])

    episodes = [
        ("blind", False),
        ("reflection", True),
    ]
    if not run_blind_first:
        episodes.reverse()

    blind_result = None
    reflection_result = None

    for mode_name, use_ref in episodes:
        yield {"type": "phase_start", "mode": mode_name, "task_name": task_name}

        # Blind: 1 shot. Reflection: 8 steps.
        steps = 1 if mode_name == "blind" else 8
        for event in _run_single_episode_stream(task_name, use_reflection=use_ref, max_steps=steps):
            yield event
            if event["type"] == "phase_end":
                if mode_name == "blind":
                    blind_result = event["result"]
                else:
                    reflection_result = event["result"]

    # Final comparison
    if blind_result and reflection_result:
        comparison = _build_comparison(blind_result, reflection_result)
        yield {
            "type": "complete",
            "experiment_id": experiment_id,
            "task_name": task_name,
            "blind": blind_result,
            "reflection": reflection_result,
            "comparison": comparison,
        }
