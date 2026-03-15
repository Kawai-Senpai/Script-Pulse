from __future__ import annotations

from typing import Any, Dict, List, Optional

from .serialization import serialize_for_prompt

REGENERATION_CONTEXT_GUIDE = (
    "If regeneration context is provided, use it to revise your output. "
    "Prioritize the script text, then apply regeneration instructions. "
    "When a previous report is present, treat it as a baseline to improve."
)


def build_regeneration_context_messages(
    regeneration_prompt: Optional[str],
    previous_report: Optional[Any],
    validator_instructions: Optional[List[str]],
) -> List[str]:
    messages: List[str] = []

    has_context = bool(regeneration_prompt or previous_report or validator_instructions)
    if has_context:
        messages.append(REGENERATION_CONTEXT_GUIDE)

    if regeneration_prompt:
        messages.append(f"User regeneration prompt:\n{regeneration_prompt}")

    if previous_report is not None:
        if hasattr(previous_report, "model_dump"):
            report_payload = previous_report.model_dump()
        else:
            report_payload = previous_report
        messages.append(
            f"Previous report:\n{serialize_for_prompt(report_payload)}"
        )

    if validator_instructions:
        joined = "\n".join(validator_instructions).strip()
        if joined:
            messages.append(f"Validator regeneration instructions:\n{joined}")

    return messages
