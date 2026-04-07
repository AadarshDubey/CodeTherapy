"""Observation model returned by the environment at each step."""

from typing import List, Optional
from pydantic import BaseModel, Field


class DebugObservation(BaseModel):
    """
    Observation returned after reset() or step().

    Contains all information the agent needs to decide its next action:
    the current buggy code, test execution results, and a prompt
    guiding the agent to write a structured reflection.
    """

    buggy_code: str = Field(
        ...,
        description="The current version of the code under test.",
    )
    test_output: str = Field(
        default="",
        description="Stdout/stderr captured from running the test suite.",
    )
    tests_passed: int = Field(
        default=0,
        description="Number of tests that passed in the last run.",
    )
    tests_total: int = Field(
        default=0,
        description="Total number of tests in the suite.",
    )
    reflection_prompt: str = Field(
        default="",
        description=(
            "Structured prompt asking the agent to provide a reflection "
            "in the Hypothesis → Action → Result format."
        ),
    )
    task_description: str = Field(
        default="",
        description="Human-readable description of what the task requires.",
    )
    step_number: int = Field(
        default=0,
        description="Current step index (1-based).",
    )
    max_steps: int = Field(
        default=8,
        description="Maximum number of steps allowed in this episode.",
    )
    done: bool = Field(
        default=False,
        description="Whether the episode has ended.",
    )
    reward: Optional[float] = Field(
        default=None,
        description="Reward for this step, or None on reset.",
    )
    last_action_error: Optional[str] = Field(
        default=None,
        description="Error message if the last action failed, else null.",
    )
    reward_breakdown: Optional[dict] = Field(
        default=None,
        description="Detailed breakdown of the reward components.",
    )
