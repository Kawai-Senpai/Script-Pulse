from __future__ import annotations

from typing import Any, Dict, List, Type

from pydantic import BaseModel


def parse_schema(schema_cls: Type[BaseModel], payload: Any) -> BaseModel:
    if payload is None:
        raise ValueError("Empty response from model")

    if isinstance(payload, dict) and list(payload.keys()) == ["content"]:
        payload = payload.get("content")

    if isinstance(payload, schema_cls):
        return payload

    if isinstance(payload, dict):
        return schema_cls.model_validate(payload)

    if isinstance(payload, str):
        return schema_cls.model_validate_json(payload)

    raise TypeError(f"Unsupported response type for {schema_cls.__name__}: {type(payload)}")


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    return model.model_dump()


def build_summary_from_beats(beat_extraction) -> List[str]:
    lines: List[str] = []
    if getattr(beat_extraction, "premise", None):
        lines.append(beat_extraction.premise)

    for beat in getattr(beat_extraction, "beats", []):
        if len(lines) >= 4:
            break
        short_description = getattr(beat, "short_description", "")
        if short_description and short_description not in lines:
            lines.append(short_description)

    return lines[:4]
