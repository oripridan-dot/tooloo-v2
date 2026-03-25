"""
engine/intent.py - Data models for Intent, Validation, and Remediation.

These Pydantic models provide a structured format for the "Intent-Gap-Remediation"
workflow, ensuring consistency between the different stages of the execution
and validation loop.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IntentPayload(BaseModel):
    """
    Defines the structured intent of an LLM agent before execution.
    This is the "plan" that will be validated against.
    """
    intent_description: str = Field(
        ...,
        description="A clear, one-sentence description of the goal."
    )
    target_resource: str = Field(
        ...,
        description="The primary file or resource that will be modified."
    )
    expected_outcome_description: str = Field(
        ...,
        description="A specific, verifiable description of the state of the target "
                    "resource after a successful operation."
    )


class ValidationResult(BaseModel):
    """
    Represents the outcome of comparing the IntentPayload against the
    actual result of an operation.
    """
    is_success: bool = Field(
        ...,
        description="True if the actual outcome matches the expected outcome, False otherwise."
    )
    intent_gap: str | None = Field(
        default=None,
        description="A description of the discrepancy between the expected and actual "
                    "outcomes. Null if is_success is True."
    )
    actual_outcome: str = Field(
        ...,
        description="A summary of what actually happened."
    )


class RemediationPlan(BaseModel):
    """
    A set of steps to correct an intent_gap.
    """
    remediation_steps: list[str] = Field(
        default_factory=list,
        description="A list of concrete actions to take to fix the intent gap."
    )
    new_mandate: str = Field(
        ...,
        description="A revised mandate to be sent back to the executor to enact the remediation."
    )

