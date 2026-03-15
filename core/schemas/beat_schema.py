from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import StrictBaseModel

BeatLabel = Literal[
    "setup",
    "inciting_incident",
    "conflict",
    "reveal",
    "escalation",
    "decision",
    "cliffhanger",
    "resolution",
    "other",
]


class StoryBeat(StrictBaseModel):
    beat_id: str = Field(..., description="Unique beat id like 'B1'.")
    label: BeatLabel = Field(..., description="Beat label from the allowed set.")
    short_description: str = Field(
        ..., description="Concise description grounded in the script."
    )
    involved_characters: List[str] = Field(
        default_factory=list, description="Characters present in this beat."
    )
    evidence_line_ids: List[str] = Field(
        default_factory=list, description="Line ids that support this beat."
    )
    tension_level: int = Field(
        ..., ge=1, le=5, description="Tension level from 1 (low) to 5 (high)."
    )


class BeatExtraction(StrictBaseModel):
    premise: str = Field(..., description="One-sentence premise grounded in the script.")
    beats: List[StoryBeat] = Field(
        default_factory=list, description="Ordered list of extracted beats."
    )
    central_conflict: str = Field(..., description="Core conflict stated plainly.")
    key_reveal: Optional[str] = Field(
        default=None, description="Most important reveal if present."
    )
    unresolved_questions: List[str] = Field(
        default_factory=list, description="Open questions left by the scene."
    )
    probable_cliffhanger_beat_id: Optional[str] = Field(
        default=None, description="Beat id most likely to act as a cliffhanger."
    )
