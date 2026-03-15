from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple

from ultragpt import UltraGPT
from ultraprint.logging import logger

from ..config import log_config
from ..keys.key import openrouter_api_key
from ..utils.analysis_utils import resolve_token_count


log = logger("llm_log", **log_config)
_ultragpt_instance: Optional[UltraGPT] = None
_ultragpt_lock = threading.Lock()


def get_ultragpt() -> UltraGPT:
    global _ultragpt_instance
    if _ultragpt_instance is None:
        with _ultragpt_lock:
            if _ultragpt_instance is None:
                log.info("Creating UltraGPT instance (lazy init)")
                _ultragpt_instance = UltraGPT(
                    openrouter_api_key=openrouter_api_key,
                    verbose=False,
                    log_extra_info=log_config.get("include_extra_info", False),
                    log_to_file=log_config.get("write_to_file", False),
                    log_level=log_config.get("log_level", "INFO"),
                    max_tokens=None,
                )
    return _ultragpt_instance


def send_ultragpt_chat(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float,
    response_format: Any = None,
    reasoning_iterations: int = 2,
    steps_pipeline: bool = False,
    reasoning_pipeline: bool = False,
    steps_model: Optional[str] = None,
    reasoning_model: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    tools_config: Optional[Dict[str, Any]] = None,
    max_tokens: Optional[int] = None,
    reserve_ratio: Optional[float] = None,
) -> Tuple[Any, int, Dict[str, Any]]:
    if tools is None:
        tools = []

    log.info(
        "UltraGPT chat | model=%s messages=%d schema=%s temperature=%.2f",
        model,
        len(messages),
        getattr(response_format, "__name__", "none") if response_format else "none",
        float(temperature),
    )

    try:
        content, total_tokens, details = get_ultragpt().chat(
            model=model,
            messages=messages,
            temperature=temperature,
            schema=response_format,
            reasoning_iterations=reasoning_iterations,
            steps_pipeline=steps_pipeline,
            reasoning_pipeline=reasoning_pipeline,
            steps_model=steps_model,
            reasoning_model=reasoning_model,
            tools=tools,
            tools_config=tools_config,
            max_tokens=max_tokens,
            reserve_ratio=reserve_ratio,
        )
    except Exception as exc:
        log.error("UltraGPT chat failed: %s", exc)
        raise exc

    normalized_details = details or {}
    resolved_total_tokens = resolve_token_count(total_tokens, normalized_details)
    normalized_details["resolved_total_tokens"] = resolved_total_tokens

    return content, resolved_total_tokens, normalized_details
