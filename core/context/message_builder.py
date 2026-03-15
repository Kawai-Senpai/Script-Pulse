from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from ..prompts import (
    BEAT_SYSTEM_PROMPT,
    BEAT_USER_PROMPT_TEMPLATE,
    CRITIQUE_SYSTEM_PROMPT,
    CRITIQUE_USER_PROMPT_TEMPLATE,
    EMOTION_SYSTEM_PROMPT,
    EMOTION_USER_PROMPT_TEMPLATE,
    ENGAGEMENT_SYSTEM_PROMPT,
    ENGAGEMENT_USER_PROMPT_TEMPLATE,
    VALIDATOR_SYSTEM_PROMPT,
    VALIDATOR_USER_PROMPT_TEMPLATE,
)
from .serialization import serialize_for_prompt

Message = Dict[str, str]


def build_messages(
    system_prompt: str,
    context_messages: Iterable[str],
    instruction: str,
) -> List[Message]:
    messages: List[Message] = []
    for message in context_messages:
        messages.append({"role": "user", "content": message})
    messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": instruction})
    return messages


def _block(label: str, content: Optional[object]) -> str:
    safe_content = "" if content is None else serialize_for_prompt(content)
    return f"{label}:\n{safe_content}".strip()


def _compose_messages(
    system_prompt: str,
    context_blocks: Iterable[str],
    instruction: str,
    extra_user_messages: Optional[Iterable[str]] = None,
) -> List[Message]:
    user_messages = list(context_blocks)
    if extra_user_messages:
        user_messages.extend(extra_user_messages)
    return build_messages(system_prompt, user_messages, instruction)


def build_beat_messages(
    script_with_line_ids: str,
    extra_user_messages: Optional[Iterable[str]] = None,
) -> List[Message]:
    return _compose_messages(
        BEAT_SYSTEM_PROMPT,
        [_block("Script", script_with_line_ids)],
        BEAT_USER_PROMPT_TEMPLATE,
        extra_user_messages,
    )


def build_emotion_messages(
    script_with_line_ids: str,
    beat_extraction_json: str,
    extra_user_messages: Optional[Iterable[str]] = None,
) -> List[Message]:
    return _compose_messages(
        EMOTION_SYSTEM_PROMPT,
        [
            _block("Script", script_with_line_ids),
            _block("Beat extraction", beat_extraction_json),
        ],
        EMOTION_USER_PROMPT_TEMPLATE,
        extra_user_messages,
    )


def build_engagement_messages(
    script_with_line_ids: str,
    rubric_bundle_json: str,
    extra_user_messages: Optional[Iterable[str]] = None,
) -> List[Message]:
    return _compose_messages(
        ENGAGEMENT_SYSTEM_PROMPT,
        [
            _block("Rubric", rubric_bundle_json),
            _block("Script", script_with_line_ids),
        ],
        ENGAGEMENT_USER_PROMPT_TEMPLATE,
        extra_user_messages,
    )


def build_critique_messages(
    script_with_line_ids: str,
    beat_extraction_json: str,
    emotion_analysis_json: str,
    engagement_analysis_json: str,
    extra_user_messages: Optional[Iterable[str]] = None,
) -> List[Message]:
    return _compose_messages(
        CRITIQUE_SYSTEM_PROMPT,
        [
            _block("Script", script_with_line_ids),
            _block("Beat extraction", beat_extraction_json),
            _block("Emotion analysis", emotion_analysis_json),
            _block("Engagement analysis", engagement_analysis_json),
        ],
        CRITIQUE_USER_PROMPT_TEMPLATE,
        extra_user_messages,
    )


def build_validation_messages(
    script_with_line_ids: str,
    engagement_analysis_json: str,
    final_report_json: str,
    extra_user_messages: Optional[Iterable[str]] = None,
) -> List[Message]:
    return _compose_messages(
        VALIDATOR_SYSTEM_PROMPT,
        [
            _block("Script", script_with_line_ids),
            _block("Engagement analysis", engagement_analysis_json),
            _block("Final report", final_report_json),
        ],
        VALIDATOR_USER_PROMPT_TEMPLATE,
        extra_user_messages,
    )
