from __future__ import annotations

import json
from typing import Any


def serialize_for_prompt(value: Any) -> str:
    """Return a compact, stable string for prompt injection.

    - Dict inputs are compact JSON with sorted keys.
    - All other inputs fall back to string conversion.
    """
    try:
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        return str(value)
    except Exception:
        return str(value)
