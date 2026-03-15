from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import StrictBaseModel

TargetArea = Literal["opening", "dialogue", "pacing", "conflict", "ending", "emotion"]


class RewriteSuggestion(StrictBaseModel):
    target_area: TargetArea = Field(..., description="Where the suggestion applies.")
    issue: str = Field(..., description="Specific issue observed in the script.")
    why_it_hurts_engagement: str = Field(
        ..., description="Why this issue reduces engagement."
    )
    concrete_fix: str = Field(..., description="Actionable fix to apply.")
    target_line_ids: List[str] = Field(
        default_factory=list, description="Line ids the fix should target."
    )
    example_rewrite: Optional[str] = Field(
        default=None, description="Optional sample rewrite snippet."
    )


class ImprovementPlan(StrictBaseModel):
    top_3_priorities: List[str] = Field(
        default_factory=list, description="Three highest-impact priorities."
    )
    suggestions: List[RewriteSuggestion] = Field(
        default_factory=list, description="Concrete improvement suggestions."
    )
    optional_stronger_opening: Optional[str] = Field(
        default=None, description="Optional stronger opening line rewrite."
    )
