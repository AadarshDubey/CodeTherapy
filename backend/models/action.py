"""Action model representing an agent's debugging attempt."""

from typing import List
from pydantic import BaseModel, Field


class CodeEdit(BaseModel):
    """A specific search-and-replace edit."""
    search: str = Field(..., description="The exact code block to search for.")
    replace: str = Field(..., description="The code to replace it with.")


class DebugAction(BaseModel):
    """
    An action submitted by the agent at each step.

    The agent must provide code edits AND a structured reflection.
    The reflection quality directly contributes to the reward signal.
    """

    edits: List[CodeEdit] = Field(
        ...,
        description="A list of code edits to apply.",
    )
    hypothesis: str = Field(
        ...,
        description=(
            "The agent's hypothesis about why the bug exists. "
            "Should reference specific code constructs."
        ),
    )
    action_description: str = Field(
        ...,
        description=(
            "What the agent changed and why. "
            "Should describe the concrete modification made."
        ),
    )
    expected_result: str = Field(
        ...,
        description=(
            "What the agent expects to happen after the fix. "
            "Should logically follow from the action taken."
        ),
    )
