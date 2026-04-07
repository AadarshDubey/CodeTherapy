"""State model for environment metadata."""

from typing import Optional
from pydantic import BaseModel, Field


class DebugState(BaseModel):
    """
    Environment state / metadata.

    Returned by the state() endpoint. Contains information about the
    current episode that may not be visible in the observation.
    """

    episode_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the current episode.",
    )
    step_count: int = Field(
        default=0,
        description="Number of steps taken so far in this episode.",
    )
    task_name: str = Field(
        default="",
        description="Name of the currently loaded task.",
    )
    max_steps: int = Field(
        default=8,
        description="Maximum number of steps allowed.",
    )
    current_code: str = Field(
        default="",
        description="The current version of the code being debugged.",
    )
    best_score: float = Field(
        default=0.0,
        description="Best combined reward achieved so far in this episode.",
    )
    tests_passed: int = Field(
        default=0,
        description="Number of tests currently passing.",
    )
    tests_total: int = Field(
        default=0,
        description="Total number of tests for this task.",
    )
