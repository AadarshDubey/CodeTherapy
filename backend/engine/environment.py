"""
Debug Environment — OpenEnv-compliant environment for reflection-guided debugging.

Implements the standard reset() / step() / state interface.
The environment simulates a software engineer iteratively debugging code,
scoring both code correctness AND reflection quality.

Key feature: RATCHET — progress is never lost. If the agent's edits make
things worse, the code reverts to the best-known version.
"""

import uuid
from typing import Optional, List, Dict, Any

from backend.models.observation import DebugObservation
from backend.models.action import DebugAction, CodeEdit
from backend.models.state import DebugState
from backend.models.reward import RewardBreakdown
from backend.tasks import TASK_REGISTRY
from backend.engine.reflection_scorer import ReflectionScorer


class DebugEnvironment:
    """
    OpenEnv-compliant debugging environment.

    Attributes:
        MAX_STEPS: Maximum debugging attempts per episode.
        REWARD_WEIGHT_CODE: Weight for code correctness in combined reward.
        REWARD_WEIGHT_REFLECTION: Weight for reflection quality in combined reward.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True
    MAX_STEPS = 8
    REWARD_WEIGHT_CODE = 0.6
    REWARD_WEIGHT_REFLECTION = 0.4

    def __init__(self, use_reflection: bool = True):
        self._state = DebugState()
        self._task = None
        self._use_reflection = use_reflection
        self._scorer = ReflectionScorer() if use_reflection else None
        self._prev_tests_passed = 0
        self._best_tests_passed = 0
        self._best_code = None
        self._history: List[Dict[str, Any]] = []
        self._current_task_name = "api_json_fix"  # default

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_name: Optional[str] = None,
        **kwargs,
    ) -> DebugObservation:
        """
        Reset the environment for a new debugging episode.

        Args:
            seed: Optional random seed (not used currently).
            episode_id: Optional episode identifier.
            task_name: Name of the task to load (from TASK_REGISTRY).

        Returns:
            Initial DebugObservation with the buggy code and test results.
        """
        # Select task
        if task_name == "custom":
            from backend.tasks.custom_task import CustomTask
            self._current_task_name = "custom"
            buggy = kwargs.get("custom_buggy_code") or ""
            tests = kwargs.get("custom_test_code") or ""
            self._task = CustomTask(buggy, tests)
        else:
            if task_name and task_name in TASK_REGISTRY:
                self._current_task_name = task_name
            self._task = TASK_REGISTRY[self._current_task_name]

        # Run tests on the original buggy code to show initial failures
        tests_passed, tests_total, test_output = self._task.run_tests(
            self._task.buggy_code
        )

        # Initialize state
        eid = episode_id or str(uuid.uuid4())
        
        # Strip trailing whitespaces from lines to ensure robust search-and-replace
        normalized_buggy_code = "\n".join(line.rstrip() for line in self._task.buggy_code.split("\n"))
        
        self._state = DebugState(
            episode_id=eid,
            step_count=0,
            task_name=self._current_task_name,
            max_steps=self.MAX_STEPS,
            current_code=normalized_buggy_code,
            best_score=0.0,
            tests_passed=tests_passed,
            tests_total=tests_total,
        )
        self._prev_tests_passed = tests_passed
        self._best_tests_passed = tests_passed
        self._best_code = normalized_buggy_code
        self._history = []
        self.messages = None

        reflection_prompt = self._task.get_reflection_prompt(0, test_output)

        return DebugObservation(
            buggy_code=self._task.buggy_code,
            test_output=test_output,
            tests_passed=tests_passed,
            tests_total=tests_total,
            reflection_prompt=reflection_prompt,
            task_description=self._task.description,
            step_number=0,
            max_steps=self.MAX_STEPS,
            done=False,
            reward=None,
            last_action_error=None,
            reward_breakdown=None,
        )

    # ─── Edit Application ─────────────────────────────────────────────

    def _apply_edits(self, code: str, edits: List[CodeEdit]) -> str:
        """Apply search-and-replace edits to code. Tries exact match first,
        then falls back to indentation-flexible matching."""
        for edit in edits:
            search_str = edit.search if hasattr(edit, "search") else edit.get("search", "")
            replace_str = edit.replace if hasattr(edit, "replace") else edit.get("replace", "")
            
            # Normalize trailing whitespace
            search_str = "\n".join(line.rstrip() for line in search_str.split("\n"))
            replace_str = "\n".join(line.rstrip() for line in replace_str.split("\n"))
            
            if not search_str:
                continue

            if search_str in code:
                code = code.replace(search_str, replace_str, 1)
            else:
                code = self._fuzzy_replace(code, search_str, replace_str)
        return code

    def _fuzzy_replace(self, code: str, search_str: str, replace_str: str) -> str:
        """Match search_str ignoring indentation differences, then apply
        replacement with correct indentation for the code context."""
        search_lines = search_str.split("\n")
        code_lines = code.split("\n")

        search_stripped = [line.lstrip() for line in search_lines]
        # Remove empty lines at edges
        while search_stripped and not search_stripped[0].strip():
            search_stripped.pop(0)
            search_lines.pop(0)
        while search_stripped and not search_stripped[-1].strip():
            search_stripped.pop()
            search_lines.pop()

        if not search_stripped:
            raise ValueError("Search block is empty after stripping")

        num_search = len(search_lines)

        for i in range(len(code_lines) - num_search + 1):
            window = code_lines[i:i + num_search]
            window_stripped = [line.lstrip() for line in window]

            if window_stripped == search_stripped:
                # Calculate indentation delta
                first_code = next((l for l in window if l.strip()), "")
                first_search = next((l for l in search_lines if l.strip()), "")
                code_indent = len(first_code) - len(first_code.lstrip())
                search_indent = len(first_search) - len(first_search.lstrip())
                delta = code_indent - search_indent

                # Adjust replacement indentation
                replace_lines = replace_str.split("\n")
                adjusted = []
                for rline in replace_lines:
                    if not rline.strip():
                        adjusted.append("")
                    elif delta > 0:
                        adjusted.append(" " * delta + rline)
                    elif delta < 0:
                        cur = len(rline) - len(rline.lstrip())
                        adjusted.append(" " * max(0, cur + delta) + rline.lstrip())
                    else:
                        adjusted.append(rline)

                original_block = "\n".join(window)
                adjusted_block = "\n".join(adjusted)
                return code.replace(original_block, adjusted_block, 1)

        raise ValueError(f"Search block not found in current code:\n{search_str}")

    # ─── Step ─────────────────────────────────────────────────────────

    def step(
        self,
        action: DebugAction,
        timeout_s: Optional[float] = None,
        **kwargs,
    ) -> DebugObservation:
        """
        Execute one debugging step.

        Simple flow:
        1. Apply edits → run tests
        2. If edits fail or cause syntax error → revert, report real state
        3. If regression → revert to best-known code
        4. Score reflection + compute reward
        """
        if self._task is None:
            return self._error_observation("No task loaded. Call reset() first.")

        self._state.step_count += 1
        step_num = self._state.step_count
        error_msg = None

        # 1. Apply edits and run tests
        new_code = self._state.current_code
        try:
            new_code = self._apply_edits(new_code, action.edits)
            tests_passed, tests_total, test_output = self._task.run_tests(new_code)
        except Exception as e:
            # Edits failed — revert, report real state
            error_msg = str(e)
            new_code = self._state.current_code
            tests_passed, tests_total, test_output = self._task.run_tests(new_code)
            test_output = (
                f"⚠️ Edit failed: {error_msg}\n"
                f"Code unchanged ({tests_passed}/{tests_total} passing).\n\n"
                f"{test_output}"
            )

        # 2. Handle syntax errors — revert
        if "Code execution error:" in test_output and (
            "SyntaxError" in test_output or "IndentationError" in test_output
        ):
            error_msg = "Syntax error in edited code"
            new_code = self._state.current_code
            tests_passed, tests_total, test_output = self._task.run_tests(new_code)
            test_output = (
                f"⚠️ Your edits caused a syntax error. Code reverted.\n"
                f"Current state: {tests_passed}/{tests_total} passing.\n\n"
                f"{test_output}"
            )

        # 3. RATCHET: regression → revert to best
        if tests_passed < self._best_tests_passed and self._best_code is not None:
            error_msg = f"Regression: {tests_passed} < best {self._best_tests_passed}"
            new_code = self._best_code
            tests_passed, tests_total, test_output = self._task.run_tests(new_code)
            test_output = (
                f"⚠️ Your edits broke previously passing tests. "
                f"Code reverted to best version ({self._best_tests_passed}/{tests_total}).\n"
                f"Try a DIFFERENT approach.\n\n"
                f"{test_output}"
            )

        # Update best (ratchet only goes forward)
        if tests_passed > self._best_tests_passed:
            self._best_code = new_code
            self._best_tests_passed = tests_passed

        # 4. Score code correctness
        code_correctness = self._task.grade(tests_passed, tests_total)

        # 5. Score reflection quality
        if self._use_reflection and self._scorer:
            reflection_result = self._scorer.score(
                hypothesis=action.hypothesis,
                action_description=action.action_description,
                expected_result=action.expected_result,
                prev_tests_passed=self._prev_tests_passed,
                curr_tests_passed=tests_passed,
                tests_total=tests_total,
            )
        else:
            reflection_result = {
                "combined": 0.0, "s_improve": 0.0,
                "s_bug": 0.0, "s_fix": 0.0, "s_res": 0.0,
            }
        reflection_quality = reflection_result["combined"]

        # 6. Compute reward
        combined_reward = round(
            self.REWARD_WEIGHT_CODE * code_correctness
            + self.REWARD_WEIGHT_REFLECTION * reflection_quality,
            4,
        )
        combined_reward = min(max(combined_reward, 0.01), 0.99)

        reward_breakdown = RewardBreakdown(
            code_correctness=code_correctness,
            reflection_quality=reflection_quality,
            combined_reward=combined_reward,
            tests_improved=tests_passed > self._prev_tests_passed,
            reflection_sub_scores=reflection_result,
        )

        # 7. Update state
        self._state.current_code = new_code
        self._state.tests_passed = tests_passed
        self._state.tests_total = tests_total
        if combined_reward > self._state.best_score:
            self._state.best_score = combined_reward

        self._history.append({
            "step": step_num,
            "tests_passed": tests_passed,
            "tests_total": tests_total,
            "code_correctness": code_correctness,
            "reflection_quality": reflection_quality,
            "reflection_sub_scores": reflection_result,
            "combined_reward": combined_reward,
            "hypothesis": action.hypothesis[:200],
            "action_description": action.action_description[:200],
            "expected_result": action.expected_result[:200],
        })

        # 8. Check termination
        done = (tests_passed == tests_total and tests_total > 0) or step_num >= self.MAX_STEPS
        reflection_prompt = self._task.get_reflection_prompt(step_num, test_output)
        self._prev_tests_passed = tests_passed

        return DebugObservation(
            buggy_code=new_code,
            test_output=test_output,
            tests_passed=tests_passed,
            tests_total=tests_total,
            reflection_prompt=reflection_prompt,
            task_description=self._task.description,
            step_number=step_num,
            max_steps=self.MAX_STEPS,
            done=done,
            reward=combined_reward,
            last_action_error=error_msg,
            reward_breakdown=reward_breakdown.model_dump(),
        )

    # ─── Properties ───────────────────────────────────────────────────

    @property
    def state(self) -> DebugState:
        """Return current environment state metadata."""
        return self._state

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Return the step history for this episode."""
        return self._history

    def _error_observation(self, error: str) -> DebugObservation:
        """Create an error observation when something goes wrong."""
        return DebugObservation(
            buggy_code="",
            test_output="",
            tests_passed=0,
            tests_total=0,
            reflection_prompt="",
            task_description="",
            step_number=self._state.step_count,
            max_steps=self.MAX_STEPS,
            done=True,
            reward=0.01,
            last_action_error=error,
            reward_breakdown=None,
        )
