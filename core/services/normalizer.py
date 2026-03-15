from __future__ import annotations

import re
from typing import List, Optional

from ..schemas.input_schema import ScriptInput, ScriptLine

_DIALOGUE_RE = re.compile(r"^([A-Z][A-Za-z0-9 _\-\.()]{0,60}):\s*(.+)$")
_SCENE_RE = re.compile(r"^(INT\.|EXT\.|INT/EXT\.|EST\.|SCENE)(\s|$)", re.IGNORECASE)
_NON_CHARACTER_LABELS = {"TITLE", "SCENE"}


def _normalize_lines(raw_text: str) -> List[str]:
    stripped = raw_text.strip()
    if not stripped:
        return []
    return [line.strip() for line in stripped.splitlines()]


def _is_dialogue_line(line: str) -> bool:
    return bool(_DIALOGUE_RE.match(line))


def _is_scene_heading(line: str) -> bool:
    return bool(_SCENE_RE.match(line))


def _normalize_character_name(name: str) -> str:
    name = re.sub(r"\s*\(.*?\)\s*", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    if name.isupper():
        return name.title()
    return name


def _extract_characters(lines: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for line in lines:
        match = _DIALOGUE_RE.match(line)
        if not match:
            continue
        name = _normalize_character_name(match.group(1))
        if name.upper() in _NON_CHARACTER_LABELS:
            continue
        if not name or name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def _detect_format(lines: List[str]) -> str:
    has_dialogue = any(_is_dialogue_line(line) for line in lines)
    has_scene = any(_is_scene_heading(line) for line in lines)
    if has_dialogue and has_scene:
        return "scene_dialogue"
    if has_dialogue:
        return "dialogue"
    if has_scene:
        return "mixed"
    return "unknown"


def normalize_script_input(raw_text: str, title: Optional[str] = None) -> ScriptInput:
    if raw_text is None:
        raise ValueError("raw_text is required")

    lines = _normalize_lines(raw_text)
    normalized_text = "\n".join(lines)
    structured_lines = [
        ScriptLine(line_id=f"L{idx}", line_number=idx, text=line)
        for idx, line in enumerate(lines, start=1)
    ]
    line_map = [f"{line.line_id}: {line.text}" for line in structured_lines]

    return ScriptInput(
        title=title,
        raw_text=raw_text,
        normalized_text=normalized_text,
        lines=structured_lines,
        line_map=line_map,
        detected_characters=_extract_characters(lines),
        script_format=_detect_format(lines),
    )
