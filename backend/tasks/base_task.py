"""Abstract base class for all debugging tasks."""

from abc import ABC, abstractmethod
from typing import Tuple


class BaseTask(ABC):
    """
    Base class for debugging tasks.

    Each task provides:
    - A buggy code snippet
    - A test suite (as executable Python code)
    - A human-readable description
    - A grader that returns a score in [0.0, 1.0]

    Subclasses must implement run_tests() and grade().
    """

    name: str = ""
    difficulty: str = ""  # "easy" | "medium" | "hard"
    description: str = ""
    buggy_code: str = ""
    test_code: str = ""
    hint: str = ""

    @abstractmethod
    def run_tests(self, code: str) -> Tuple[int, int, str]:
        """
        Execute the test suite against the provided code.

        Args:
            code: The (potentially fixed) code to test.

        Returns:
            Tuple of (tests_passed, tests_total, output_string).
            output_string contains captured stdout/stderr from test execution.
        """
        pass

    @abstractmethod
    def grade(self, tests_passed: int, tests_total: int) -> float:
        """
        Compute a score in [0.0, 1.0] from test results.

        Args:
            tests_passed: Number of tests that passed.
            tests_total: Total number of tests.

        Returns:
            Float score in [0.0, 1.0].
        """
        pass

    def get_reflection_prompt(self, step: int, test_output: str) -> str:
        """
        Generate a structured reflection prompt for the agent.

        Args:
            step: Current step number.
            test_output: Output from the last test run.

        Returns:
            A prompt string guiding the agent to produce H→A→R reflection.
        """
        return (
            f"Step {step} Reflection Required:\n"
            f"You are debugging: {self.description}\n\n"
            f"Test Results:\n{test_output}\n\n"
            "Please provide your response as JSON with these exact fields:\n"
            "{\n"
            '  "hypothesis": "Why does the bug exist? Reference specific code constructs.",\n'
            '  "action_description": "What will you change and why?",\n'
            '  "expected_result": "What do you expect after applying the fix?",\n'
            '  "edits": [{"search": "old code...", "replace": "new code..."}]\n'
            "}\n"
        )
