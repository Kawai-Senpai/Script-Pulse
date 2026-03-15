from __future__ import annotations

from typing import List, Literal

from pydantic import Field

from .base import StrictBaseModel

EmotionLabel = Literal[
    "grief",
    "guilt",
    "anger",
    "fear",
    "hope",
    "tension",
    "sadness",
    "relief",
    "shock",
    "longing",
    "resentment",
    "uncertainty",
]


class EmotionTag(StrictBaseModel):
    emotion: EmotionLabel = Field(..., description="Emotion label.")
    strength: int = Field(..., ge=1, le=5, description="Emotion strength 1 to 5.")
    justification: str = Field(..., description="Short grounded explanation.")
    evidence_line_ids: List[str] = Field(
        default_factory=list, description="Line ids that support the emotion."
    )


class EmotionalShift(StrictBaseModel):
    beat_id: str = Field(..., description="Beat id from BeatExtraction.")
    dominant_emotions: List[EmotionTag] = Field(
        default_factory=list, description="Dominant emotions for this beat."
    )
    shift_from_previous: str = Field(
        ..., description="How the emotion changes vs the previous beat."
    )
    emotional_intensity: int = Field(
        ..., ge=1, le=10, description="Overall intensity 1 to 10."
    )


class EmotionAnalysis(StrictBaseModel):
    overall_tone: List[str] = Field(
        default_factory=list, description="High-level tone words for the scene."
    )
    dominant_scene_emotions: List[EmotionTag] = Field(
        default_factory=list, description="Dominant emotions across the full scene."
    )
    emotional_arc_summary: str = Field(
        ..., description="Short summary of how emotion evolves."
    )
    beatwise_arc: List[EmotionalShift] = Field(
        default_factory=list, description="Beat-by-beat emotional shifts."
    )
