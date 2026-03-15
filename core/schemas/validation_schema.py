from __future__ import annotations

from typing import List

from pydantic import Field

from .base import StrictBaseModel


class ValidationReport(StrictBaseModel):
    valid: bool = Field(..., description="Whether the report passes validation.")
    errors: List[str] = Field(default_factory=list, description="Hard failures.")
    warnings: List[str] = Field(default_factory=list, description="Soft issues.")
    grounding_issues: List[str] = Field(
        default_factory=list, description="Claims not supported by the script."
    )
    score_consistency_issues: List[str] = Field(
        default_factory=list,
        description="Score mismatches or inconsistencies in the report.",
    )
    regeneration_instructions: List[str] = Field(
        default_factory=list,
        description="Concrete instructions for a full regeneration retry.",
    )
    retryable: bool = Field(
        ..., description="Whether the full pipeline should retry the loop."
    )
