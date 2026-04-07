"""Reward breakdown model for transparency in scoring."""

from pydantic import BaseModel, Field


class RewardBreakdown(BaseModel):
    """
    Detailed breakdown of how the reward was computed.

    The combined reward is a weighted sum of code correctness (how many
    tests pass) and reflection quality (how well-structured and specific
    the agent's reasoning is).

    Weights: 0.6 * code_correctness + 0.4 * reflection_quality
    """

    code_correctness: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Fraction of tests passing (tests_passed / tests_total).",
    )
    reflection_quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score from the reflection scorer (0.0–1.0).",
    )
    combined_reward: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Final weighted reward: 0.6*correctness + 0.4*reflection.",
    )
    tests_improved: bool = Field(
        default=False,
        description="Whether more tests pass than in the previous step.",
    )
    reflection_sub_scores: dict = Field(
        default_factory=dict,
        description="Detailed reflection scoring breakdown if available.",
    )
