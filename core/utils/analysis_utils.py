from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any, Dict


_STEP_KEY_RE = re.compile(r"^(?P<stage>.+)_(?P<iteration>\d+)$")
_STAGE_LABELS = {
    "beat_extraction": "Beat Extraction",
    "emotion_analysis": "Emotion Analysis",
    "engagement_analysis": "Engagement Analysis",
    "improvement_plan": "Improvement Plan",
    "validation": "Validation",
}


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def resolve_token_count(total_tokens: Any, details: Dict[str, Any] | None) -> int:
    details = details or {}

    resolved_total = _as_int(total_tokens)
    if resolved_total > 0:
        return resolved_total

    token_usage = details.get("token_usage", {}) or {}
    overall_usage = token_usage.get("overall", {}) or {}
    detail_total = _as_int(overall_usage.get("total_tokens"))
    if detail_total > 0:
        return detail_total

    final_usage = token_usage.get("final", {}) or {}
    detail_total = _as_int(final_usage.get("total_tokens"))
    if detail_total > 0:
        return detail_total

    detail_total = _as_int(details.get("total_tokens"))
    if detail_total > 0:
        return detail_total

    detail_total = _as_int(details.get("input_tokens")) + _as_int(details.get("output_tokens"))
    if detail_total > 0:
        return detail_total

    detail_total = _as_int(details.get("final_tokens"))
    if detail_total > 0:
        return detail_total

    pipeline_total = (
        _as_int(details.get("reasoning_pipeline_total_tokens"))
        + _as_int(details.get("steps_pipeline_total_tokens"))
    )
    if pipeline_total > 0:
        return pipeline_total

    pipeline_total = (
        _as_int(details.get("reasoning_tokens"))
        + _as_int(details.get("steps_tokens"))
        + _as_int(details.get("final_tokens"))
    )
    return pipeline_total


def build_token_usage(step_details: Dict[str, Any], total_tokens: int) -> Dict[str, Any]:
    by_stage: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    for key, raw_details in step_details.items():
        match = _STEP_KEY_RE.match(key)
        if not match:
            continue

        stage = match.group("stage")
        stage_bucket = by_stage.setdefault(
            stage,
            {
                "stage": stage,
                "label": _STAGE_LABELS.get(stage, stage.replace("_", " ").title()),
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "reasoning_tokens": 0,
            },
        )

        resolved_total = resolve_token_count(raw_details.get("resolved_total_tokens"), raw_details)
        stage_bucket["calls"] += 1
        stage_bucket["input_tokens"] += _as_int(raw_details.get("input_tokens"))
        stage_bucket["output_tokens"] += _as_int(raw_details.get("output_tokens"))
        stage_bucket["total_tokens"] += resolved_total
        stage_bucket["reasoning_tokens"] += _as_int(
            raw_details.get("reasoning_tokens_api", raw_details.get("reasoning_tokens"))
        )

    return {
        "total_tokens": _as_int(total_tokens),
        "input_tokens": sum(item["input_tokens"] for item in by_stage.values()),
        "output_tokens": sum(item["output_tokens"] for item in by_stage.values()),
        "reasoning_tokens": sum(item["reasoning_tokens"] for item in by_stage.values()),
        "stages": list(by_stage.values()),
    }
