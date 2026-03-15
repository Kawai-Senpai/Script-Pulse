from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, get_args

from ultraprint.logging import logger

from ..context.message_builder import (
    build_beat_messages,
    build_critique_messages,
    build_emotion_messages,
    build_engagement_messages,
    build_validation_messages,
)
from ..context.regeneration import build_regeneration_context_messages
from ..config import log_config
from ..prompts import RUBRIC_BUNDLE
from ..schemas.beat_schema import BeatExtraction
from ..schemas.critique_schema import ImprovementPlan
from ..schemas.emotion_schema import EmotionAnalysis
from ..schemas.engagement_schema import EngagementAnalysis, EngagementFactor
from ..schemas.final_schema import ScriptAnalysisReport
from ..schemas.validation_schema import ValidationReport
from ..services.llm_client import send_ultragpt_chat
from ..services.normalizer import normalize_script_input
from ..utils.schema_utils import build_summary_from_beats, model_to_dict, parse_schema


log = logger("llm_log", **log_config)


def _load_engagement_factor_weights(rubric_bundle: Dict[str, Any]) -> Dict[str, Decimal]:
    dimensions = rubric_bundle.get("dimensions") or []
    weights: Dict[str, Decimal] = {}

    for dim in dimensions:
        name = str((dim or {}).get("name") or "").strip()
        if not name:
            continue
        weight_raw = (dim or {}).get("weight", 0)
        weights[name] = Decimal(str(weight_raw))

    expected = set(get_args(EngagementFactor))
    actual = set(weights.keys())
    if expected != actual:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            "RUBRIC_BUNDLE dimensions must exactly match EngagementFactor set. "
            f"missing={missing} extra={extra}"
        )

    total = sum(weights.values(), Decimal("0"))
    if total != Decimal("1"):
        raise ValueError(
            "RUBRIC_BUNDLE weights must sum to 1.0 to keep overall_score on a 0-100 scale. "
            f"sum={total}"
        )

    return weights


def _apply_deterministic_engagement_math(
    analysis: EngagementAnalysis,
    weights: Dict[str, Decimal],
) -> EngagementAnalysis:
    total = Decimal("0")

    for factor in analysis.factors or []:
        weight = weights.get(str(factor.factor), Decimal("0"))
        score = Decimal(str(factor.score or 0))
        weighted = score * weight * Decimal("10")
        factor.weighted_score = float(weighted)
        total += weighted

    analysis.overall_score = float(total)
    return analysis


@dataclass
class AnalysisConfig:
    model: str = "gpt-5.4::medium"
    temperature: float = 0.2
    max_iterations: int = 1
    reasoning_iterations: int = 2
    steps_pipeline: bool = False
    reasoning_pipeline: bool = False
    steps_model: Optional[str] = None
    reasoning_model: Optional[str] = None
    tools: List[Any] = field(default_factory=list)
    tools_config: Optional[Dict[str, Any]] = None
    max_tokens: Optional[int] = None
    reserve_ratio: Optional[float] = None


@dataclass
class AnalysisResult:
    script_input: Any
    beat_extraction: BeatExtraction
    emotion_analysis: EmotionAnalysis
    engagement_analysis: EngagementAnalysis
    improvement_plan: ImprovementPlan
    report: ScriptAnalysisReport
    validation: Optional[ValidationReport]
    iterations: int
    tokens_used: int
    step_details: Dict[str, Any]


def run_analysis(
    raw_text: str,
    title: Optional[str] = None,
    config: Optional[AnalysisConfig] = None,
    previous_report: Optional[Any] = None,
    regeneration_prompt: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> AnalysisResult:
    config = config or AnalysisConfig()
    if config.max_iterations < 1:
        config.max_iterations = 1

    script_input = normalize_script_input(raw_text, title=title)
    script_with_line_ids = "\n".join(script_input.line_map)

    log.info(
        "Script analysis start | iterations=%d lines=%d",
        config.max_iterations,
        len(script_input.line_map),
    )
    if progress_callback:
        progress_callback(
            {
                "stage": "start",
                "status": "start",
                "iterations": config.max_iterations,
                "lines": len(script_input.line_map),
            }
        )

    total_tokens = 0
    details: Dict[str, Any] = {}
    regeneration_instructions: List[str] = []

    for iteration in range(1, config.max_iterations + 1):
        log.info("Iteration %d/%d", iteration, config.max_iterations)
        if progress_callback:
            progress_callback(
                {
                    "stage": "iteration",
                    "status": "start",
                    "iteration": iteration,
                    "max_iterations": config.max_iterations,
                }
            )
        extra_messages = build_regeneration_context_messages(
            regeneration_prompt,
            previous_report,
            regeneration_instructions,
        )

        log.debug("Regeneration context messages: %d", len(extra_messages))

        try:
            if progress_callback:
                progress_callback(
                    {
                        "stage": "beat_extraction",
                        "status": "start",
                        "iteration": iteration,
                    }
                )
            beat_messages = build_beat_messages(
                script_with_line_ids,
                extra_user_messages=extra_messages,
            )
            beat_content, beat_tokens, beat_details = send_ultragpt_chat(
                beat_messages,
                model=config.model,
                temperature=config.temperature,
                response_format=BeatExtraction,
                reasoning_iterations=config.reasoning_iterations,
                steps_pipeline=config.steps_pipeline,
                reasoning_pipeline=config.reasoning_pipeline,
                steps_model=config.steps_model,
                reasoning_model=config.reasoning_model,
                tools=config.tools,
                tools_config=config.tools_config,
                max_tokens=config.max_tokens,
                reserve_ratio=config.reserve_ratio,
            )
            beat_extraction = parse_schema(BeatExtraction, beat_content)
        except Exception as exc:
            log.error("Beat extraction failed: %s", exc)
            if progress_callback:
                progress_callback(
                    {
                        "stage": "beat_extraction",
                        "status": "error",
                        "iteration": iteration,
                        "message": str(exc),
                    }
                )
            raise exc
        total_tokens += beat_tokens
        details[f"beat_extraction_{iteration}"] = beat_details
        log.info("Beat extraction complete | tokens=%d", beat_tokens)
        if progress_callback:
            progress_callback(
                {
                    "stage": "beat_extraction",
                    "status": "complete",
                    "iteration": iteration,
                    "tokens": beat_tokens,
                }
            )

        try:
            if progress_callback:
                progress_callback(
                    {
                        "stage": "emotion_analysis",
                        "status": "start",
                        "iteration": iteration,
                    }
                )
            emotion_messages = build_emotion_messages(
                script_with_line_ids,
                model_to_dict(beat_extraction),
                extra_user_messages=extra_messages,
            )
            emotion_content, emotion_tokens, emotion_details = send_ultragpt_chat(
                emotion_messages,
                model=config.model,
                temperature=config.temperature,
                response_format=EmotionAnalysis,
                reasoning_iterations=config.reasoning_iterations,
                steps_pipeline=config.steps_pipeline,
                reasoning_pipeline=config.reasoning_pipeline,
                steps_model=config.steps_model,
                reasoning_model=config.reasoning_model,
                tools=config.tools,
                tools_config=config.tools_config,
                max_tokens=config.max_tokens,
                reserve_ratio=config.reserve_ratio,
            )
            emotion_analysis = parse_schema(EmotionAnalysis, emotion_content)
        except Exception as exc:
            log.error("Emotion analysis failed: %s", exc)
            if progress_callback:
                progress_callback(
                    {
                        "stage": "emotion_analysis",
                        "status": "error",
                        "iteration": iteration,
                        "message": str(exc),
                    }
                )
            raise exc
        total_tokens += emotion_tokens
        details[f"emotion_analysis_{iteration}"] = emotion_details
        log.info("Emotion analysis complete | tokens=%d", emotion_tokens)
        if progress_callback:
            progress_callback(
                {
                    "stage": "emotion_analysis",
                    "status": "complete",
                    "iteration": iteration,
                    "tokens": emotion_tokens,
                }
            )

        try:
            if progress_callback:
                progress_callback(
                    {
                        "stage": "engagement_scoring",
                        "status": "start",
                        "iteration": iteration,
                    }
                )
            engagement_messages = build_engagement_messages(
                script_with_line_ids,
                RUBRIC_BUNDLE,
                extra_user_messages=extra_messages,
            )
            engagement_content, engagement_tokens, engagement_details = send_ultragpt_chat(
                engagement_messages,
                model=config.model,
                temperature=config.temperature,
                response_format=EngagementAnalysis,
                reasoning_iterations=config.reasoning_iterations,
                steps_pipeline=config.steps_pipeline,
                reasoning_pipeline=config.reasoning_pipeline,
                steps_model=config.steps_model,
                reasoning_model=config.reasoning_model,
                tools=config.tools,
                tools_config=config.tools_config,
                max_tokens=config.max_tokens,
                reserve_ratio=config.reserve_ratio,
            )
            engagement_analysis = parse_schema(EngagementAnalysis, engagement_content)
            weights = _load_engagement_factor_weights(RUBRIC_BUNDLE)
            engagement_analysis = _apply_deterministic_engagement_math(engagement_analysis, weights)
        except Exception as exc:
            log.error("Engagement scoring failed: %s", exc)
            if progress_callback:
                progress_callback(
                    {
                        "stage": "engagement_scoring",
                        "status": "error",
                        "iteration": iteration,
                        "message": str(exc),
                    }
                )
            raise exc
        total_tokens += engagement_tokens
        details[f"engagement_analysis_{iteration}"] = engagement_details
        log.info("Engagement scoring complete | tokens=%d", engagement_tokens)
        if progress_callback:
            progress_callback(
                {
                    "stage": "engagement_scoring",
                    "status": "complete",
                    "iteration": iteration,
                    "tokens": engagement_tokens,
                }
            )

        try:
            if progress_callback:
                progress_callback(
                    {
                        "stage": "improvement_plan",
                        "status": "start",
                        "iteration": iteration,
                    }
                )
            critique_messages = build_critique_messages(
                script_with_line_ids,
                model_to_dict(beat_extraction),
                model_to_dict(emotion_analysis),
                model_to_dict(engagement_analysis),
                extra_user_messages=extra_messages,
            )
            critique_content, critique_tokens, critique_details = send_ultragpt_chat(
                critique_messages,
                model=config.model,
                temperature=config.temperature,
                response_format=ImprovementPlan,
                reasoning_iterations=config.reasoning_iterations,
                steps_pipeline=config.steps_pipeline,
                reasoning_pipeline=config.reasoning_pipeline,
                steps_model=config.steps_model,
                reasoning_model=config.reasoning_model,
                tools=config.tools,
                tools_config=config.tools_config,
                max_tokens=config.max_tokens,
                reserve_ratio=config.reserve_ratio,
            )
            improvement_plan = parse_schema(ImprovementPlan, critique_content)
        except Exception as exc:
            log.error("Improvement plan failed: %s", exc)
            if progress_callback:
                progress_callback(
                    {
                        "stage": "improvement_plan",
                        "status": "error",
                        "iteration": iteration,
                        "message": str(exc),
                    }
                )
            raise exc
        total_tokens += critique_tokens
        details[f"improvement_plan_{iteration}"] = critique_details
        log.info("Improvement plan complete | tokens=%d", critique_tokens)
        if progress_callback:
            progress_callback(
                {
                    "stage": "improvement_plan",
                    "status": "complete",
                    "iteration": iteration,
                    "tokens": critique_tokens,
                }
            )

        report = ScriptAnalysisReport(
            summary_3_4_lines=build_summary_from_beats(beat_extraction),
            beat_extraction=beat_extraction,
            emotion_analysis=emotion_analysis,
            engagement_analysis=engagement_analysis,
            improvement_plan=improvement_plan,
            confidence_notes=[],
        )

        try:
            if progress_callback:
                progress_callback(
                    {
                        "stage": "validation",
                        "status": "start",
                        "iteration": iteration,
                    }
                )
            validation_messages = build_validation_messages(
                script_with_line_ids,
                model_to_dict(engagement_analysis),
                model_to_dict(report),
            )
            validation_content, validation_tokens, validation_details = send_ultragpt_chat(
                validation_messages,
                model=config.model,
                temperature=config.temperature,
                response_format=ValidationReport,
                reasoning_iterations=config.reasoning_iterations,
                steps_pipeline=config.steps_pipeline,
                reasoning_pipeline=config.reasoning_pipeline,
                steps_model=config.steps_model,
                reasoning_model=config.reasoning_model,
                tools=config.tools,
                tools_config=config.tools_config,
                max_tokens=config.max_tokens,
                reserve_ratio=config.reserve_ratio,
            )
            validation = parse_schema(ValidationReport, validation_content)
        except Exception as exc:
            log.error("Validation failed: %s", exc)
            if progress_callback:
                progress_callback(
                    {
                        "stage": "validation",
                        "status": "error",
                        "iteration": iteration,
                        "message": str(exc),
                    }
                )
            raise exc
        total_tokens += validation_tokens
        details[f"validation_{iteration}"] = validation_details

        log.info(
            "Validation complete | valid=%s retryable=%s tokens=%d",
            validation.valid,
            validation.retryable,
            validation_tokens,
        )
        if progress_callback:
            progress_callback(
                {
                    "stage": "validation",
                    "status": "complete",
                    "iteration": iteration,
                    "valid": validation.valid,
                    "retryable": validation.retryable,
                    "tokens": validation_tokens,
                }
            )

        if validation.valid or not validation.retryable or iteration >= config.max_iterations:
            log.info("Script analysis complete | iterations=%d tokens=%d", iteration, total_tokens)
            if progress_callback:
                progress_callback(
                    {
                        "stage": "complete",
                        "status": "complete",
                        "iterations": iteration,
                        "tokens_used": total_tokens,
                    }
                )
            return AnalysisResult(
                script_input=script_input,
                beat_extraction=beat_extraction,
                emotion_analysis=emotion_analysis,
                engagement_analysis=engagement_analysis,
                improvement_plan=improvement_plan,
                report=report,
                validation=validation,
                iterations=iteration,
                tokens_used=total_tokens,
                step_details=details,
            )

        regeneration_instructions = list(validation.regeneration_instructions)
        log.info(
            "Retrying analysis | instructions=%d",
            len(regeneration_instructions),
        )
        if progress_callback:
            progress_callback(
                {
                    "stage": "retry",
                    "status": "start",
                    "iteration": iteration,
                    "instructions": len(regeneration_instructions),
                }
            )

    return AnalysisResult(
        script_input=script_input,
        beat_extraction=beat_extraction,
        emotion_analysis=emotion_analysis,
        engagement_analysis=engagement_analysis,
        improvement_plan=improvement_plan,
        report=report,
        validation=validation,
        iterations=config.max_iterations,
        tokens_used=total_tokens,
        step_details=details,
    )
