from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import Field

from .base import StrictBaseModel

ScriptFormat = Literal["dialogue", "scene_dialogue", "mixed", "unknown"]


class ScriptInput(StrictBaseModel):
    title: Optional[str] = Field(default=None, description="Optional script title.")
    raw_text: str = Field(..., description="Original script text as provided.")
    normalized_text: str = Field(..., description="Normalized text after cleanup.")
    line_map: List[str] = Field(
        ..., description="Line list formatted as 'L1: ...', 'L2: ...'."
    )
    detected_characters: List[str] = Field(
        default_factory=list, description="Detected character names from heuristics."
    )
    script_format: ScriptFormat = Field(
        ..., description="Best-effort format classification for the script."
    )
