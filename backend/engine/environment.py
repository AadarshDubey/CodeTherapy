"""
Debug Environment — OpenEnv-compliant environment for reflection-guided debugging.

Implements the standard reset() / step() / state interface.
The environment simulates a software engineer iteratively debugging code,
scoring both code correctness AND reflection quality.
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
        SUPPORTS_CONCURRENT_SESSIONS: Allow multiple simultaneous clients.
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
        self._history = []

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

    def _apply_edits(self, code: str, edits: List[CodeEdit]) -> str:
        for edit in edits:
            search_str = edit.search if hasattr(edit, "search") else edit.get("search", "")
            replace_str = edit.replace if hasattr(edit, "replace") else edit.get("replace", "")
            
            # Normalize trailing whitespace from agent's search/replace strings
            search_str = "\n".join(line.rstrip() for line in search_str.split("\n"))
            replace_str = "\n".join(line.rstrip() for line in replace_str.split("\n"))
            
            if search_str:
                if search_str in code:
                    # Replace only the first occurrence to be safe
                    code = code.replace(search_str, replace_str, 1)
                else:
                    raise ValueError(f"Search block not found in current code:\n{search_str}")
        return code

    def step(
        self,
        action: DebugAction,
        timeout_s: Optional[float] = None,
        **kwargs,
    ) -> DebugObservation:
        """
        Execute one debugging step.

        1. Apply edits and run tests on the new code
        2. Score the agent's reflection
        3. Compute combined reward
        4. Check termination conditions

        Args:
            action: The agent's DebugAction (code fix + reflection).

        Returns:
            DebugObservation with updated test results and reward.
        """
        if self._task is None:
            return self._error_observation("No task loaded. Call reset() first.")

        self._state.step_count += 1
        step_num = self._state.step_count
        error_msg = None

        # 1. Apply edits and execute tests on the new code
        new_code = self._state.current_code
        try:
            new_code = self._apply_edits(new_code, action.edits)
            tests_passed, tests_total, test_output = self._task.run_tests(new_code)
            
            # Revert state on syntax errors to prevent persistent mutilation
            if "Code execution error:" in test_output and ("SyntaxError" in test_output or "IndentationError" in test_output):
                test_output += "\n\n[ENVIRONMENT] Your edits caused a Python syntax error. The code has been REVERTED to the previous valid state. Please try again, ensuring your 'replace' string has exact Python indentation."
                new_code = self._state.current_code

        except Exception as e:
            tests_passed = 0
            tests_total = self._state.tests_total
            test_output = f"Error applying edits: {str(e)}\n\n[ENVIRONMENT] The code has been REVERTED. Ensure your 'search' string matches EXACTLY."
            error_msg = str(e)
            new_code = self._state.current_code

        # 2. Score code correctness
        code_correctness = self._task.grade(tests_passed, tests_total)

        # 3. Score reflection quality
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
            # Blind mode: flat scores, no LLM judge feedback
            reflection_result = {
                "combined": 0.5,
                "s_improve": 0.5,
                "s_bug": 0.5,
                "s_fix": 0.5,
                "s_res": 0.5,
            }
        reflection_quality = reflection_result["combined"]

        # 4. Compute combined reward
        combined_reward = round(
            self.REWARD_WEIGHT_CODE * code_correctness
            + self.REWARD_WEIGHT_REFLECTION * reflection_quality,
            4,
        )

        reward_breakdown = RewardBreakdown(
            code_correctness=code_correctness,
            reflection_quality=reflection_quality,
            combined_reward=combined_reward,
            tests_improved=tests_passed > self._prev_tests_passed,
            reflection_sub_scores=reflection_result,
        )

        # 5. Update state
        self._state.current_code = new_code
        self._state.tests_passed = tests_passed
        self._state.tests_total = tests_total
        if combined_reward > self._state.best_score:
            self._state.best_score = combined_reward

        # 6. Record history
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

        # 7. Check termination
        all_tests_pass = tests_passed == tests_total
        max_steps_reached = step_num >= self.MAX_STEPS
        done = all_tests_pass or max_steps_reached

        # 8. Generate next reflection prompt
        reflection_prompt = self._task.get_reflection_prompt(step_num, test_output)

        # Update prev for next step
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
            reward=0.0,
            last_action_error=error,
            reward_breakdown=None,
        )
