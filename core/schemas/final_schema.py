from __future__ import annotations

from typing import List

from pydantic import Field

from .base import StrictBaseModel
from .beat_schema import BeatExtraction
from .critique_schema import ImprovementPlan
from .emotion_schema import EmotionAnalysis
from .engagement_schema import EngagementAnalysis


class ScriptAnalysisReport(StrictBaseModel):
    summary_3_4_lines: List[str] = Field(
        ..., description="Three to four line factual summary."
    )
    beat_extraction: BeatExtraction = Field(..., description="Beat extraction output.")
    emotion_analysis: EmotionAnalysis = Field(..., description="Emotion analysis output.")
    engagement_analysis: EngagementAnalysis = Field(
        ..., description="Engagement scoring output."
    )
    improvement_plan: ImprovementPlan = Field(
        ..., description="Targeted improvement suggestions."
    )
    confidence_notes: List[str] = Field(
        default_factory=list, description="Notes about uncertainty or gaps."
    )
