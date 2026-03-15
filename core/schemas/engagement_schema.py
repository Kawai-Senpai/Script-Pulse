from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import StrictBaseModel

EngagementFactor = Literal[
    "opening_hook",
    "character_conflict",
    "tension_escalation",
    "clarity_of_stakes",
    "novelty_of_reveal",
    "emotional_payoff",
    "cliffhanger_strength",
]

ScoreBand = Literal["low", "moderate", "strong", "very_strong"]


class FactorScore(StrictBaseModel):
    factor: EngagementFactor = Field(..., description="Scored engagement factor.")
    score: int = Field(..., ge=0, le=10, description="Score from 0 to 10.")
    weighted_score: float = Field(
        ..., ge=0, le=100, description="Weighted contribution to overall score."
    )
    reasoning: str = Field(..., description="Evidence-based rationale.")
    evidence_line_ids: List[str] = Field(
        default_factory=list, description="Line ids that support the score."
    )


class EngagementAnalysis(StrictBaseModel):
    overall_score: int = Field(..., ge=0, le=100, description="Overall score 0-100.")
    score_band: ScoreBand = Field(..., description="Qualitative score band.")
    factors: List[FactorScore] = Field(
        default_factory=list, description="Per-factor scores.")
    strongest_element: str = Field(..., description="Factor with strongest evidence.")
    weakest_element: str = Field(..., description="Factor with weakest evidence.")
    retention_risks: List[str] = Field(
        default_factory=list, description="Short list of retention risks."
    )
    cliffhanger_moment_text: Optional[str] = Field(
        default=None, description="Exact cliffhanger moment text if present."
    )
    cliffhanger_reason: Optional[str] = Field(
        default=None, description="Why the cliffhanger is compelling."
    )
