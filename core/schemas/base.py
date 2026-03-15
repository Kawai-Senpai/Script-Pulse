from __future__ import annotations

from pydantic import BaseModel

try:
    from pydantic import ConfigDict

    class StrictBaseModel(BaseModel):
        model_config = ConfigDict(extra="forbid")

except ImportError:  # pragma: no cover - Pydantic v1 fallback

    class StrictBaseModel(BaseModel):
        class Config:
            extra = "forbid"


LineId = str
BeatId = str
