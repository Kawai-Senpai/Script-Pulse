import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.pipeline.run_analysis import AnalysisConfig, run_analysis
from core.services.normalizer import normalize_script_input
from ultragpt.providers.providers import BaseOpenAICompatibleProvider


class AnalysisUpdateTests(unittest.TestCase):
    def test_normalizer_returns_structured_lines(self):
        script_input = normalize_script_input(
            "Scene\nRiya: Why now?\nArjun: Because today I learned the truth.",
            title="The Last Message",
        )

        self.assertEqual(script_input.lines[0].line_id, "L1")
        self.assertEqual(script_input.lines[1].text, "Riya: Why now?")
        self.assertEqual(script_input.line_map[2], "L3: Arjun: Because today I learned the truth.")

    def test_final_iteration_runs_validation(self):
        stage_payloads = {
            "BeatExtraction": {
                "premise": "Riya receives a message from Arjun after five years.",
                "beats": [
                    {
                        "beat_id": "B1",
                        "label": "setup",
                        "short_description": "Riya receives a message from Arjun.",
                        "involved_characters": ["Riya", "Arjun"],
                        "evidence_line_ids": ["L2"],
                        "tension_level": 2,
                    }
                ],
                "central_conflict": "Riya is forced to confront Arjun's sudden return.",
                "key_reveal": "Arjun says the accident was not Riya's fault.",
                "unresolved_questions": ["Why did Arjun wait five years?"],
                "probable_cliffhanger_beat_id": "B1",
            },
            "EmotionAnalysis": {
                "overall_tone": ["tense"],
                "dominant_scene_emotions": [
                    {
                        "emotion": "tension",
                        "strength": 4,
                        "justification": "Riya questions why Arjun is contacting her now.",
                        "evidence_line_ids": ["L4"],
                    }
                ],
                "emotional_arc_summary": "The scene tightens from surprise into confrontation.",
                "beatwise_arc": [
                    {
                        "beat_id": "B1",
                        "dominant_emotions": [
                            {
                                "emotion": "tension",
                                "strength": 4,
                                "justification": "The exchange is unresolved and direct.",
                                "evidence_line_ids": ["L4", "L5"],
                            }
                        ],
                        "shift_from_previous": "Opening beat establishes immediate tension.",
                        "emotional_intensity": 5,
                    }
                ],
            },
            "EngagementAnalysis": {
                "overall_score": 61,
                "score_band": "strong",
                "factors": [
                    {
                        "factor": "opening_hook",
                        "score": 7,
                        "weighted_score": 14,
                        "reasoning": "The first exchange creates immediate curiosity.",
                        "evidence_line_ids": ["L2", "L4"],
                    },
                    {
                        "factor": "character_conflict",
                        "score": 6,
                        "weighted_score": 12,
                        "reasoning": "The conversation implies unresolved tension.",
                        "evidence_line_ids": ["L4", "L5"],
                    },
                    {
                        "factor": "tension_escalation",
                        "score": 7,
                        "weighted_score": 10.5,
                        "reasoning": "Each line sharpens the reveal.",
                        "evidence_line_ids": ["L4", "L5", "L7"],
                    },
                    {
                        "factor": "clarity_of_stakes",
                        "score": 6,
                        "weighted_score": 9,
                        "reasoning": "The accident matters, though details are limited.",
                        "evidence_line_ids": ["L5", "L7"],
                    },
                    {
                        "factor": "novelty_of_reveal",
                        "score": 6,
                        "weighted_score": 6,
                        "reasoning": "The reveal reframes the exchange.",
                        "evidence_line_ids": ["L7"],
                    },
                    {
                        "factor": "emotional_payoff",
                        "score": 5,
                        "weighted_score": 7.5,
                        "reasoning": "The reveal lands, though the reaction is brief.",
                        "evidence_line_ids": ["L7"],
                    },
                    {
                        "factor": "cliffhanger_strength",
                        "score": 7,
                        "weighted_score": 14,
                        "reasoning": "The scene ends on a consequential revelation.",
                        "evidence_line_ids": ["L7"],
                    },
                ],
                "strongest_element": "opening_hook",
                "weakest_element": "emotional_payoff",
                "retention_risks": ["The scene is very short."],
                "cliffhanger_moment_text": "Arjun: That the accident wasn't your fault.",
                "cliffhanger_reason": "It reframes the past and raises immediate questions.",
            },
            "ImprovementPlan": {
                "top_3_priorities": [
                    "Clarify the accident's stakes.",
                    "Give Riya a more distinct reaction.",
                    "Increase line-to-line friction.",
                ],
                "suggestions": [
                    {
                        "target_area": "emotion",
                        "issue": "Riya's reaction ends quickly after the reveal.",
                        "why_it_hurts_engagement": "The payoff lands before the emotional response fully registers.",
                        "concrete_fix": "Add one line that lingers on her reaction to the reveal.",
                        "target_line_ids": ["L7"],
                        "example_rewrite": None,
                    }
                ],
                "optional_stronger_opening": None,
            },
            "ValidationReport": {
                "valid": False,
                "errors": ["Improvement plan adds unsupported details."],
                "warnings": ["A few emotional claims are mildly inferential."],
                "grounding_issues": ["Suggested lines introduce facts not present in the script."],
                "score_consistency_issues": [],
                "regeneration_instructions": [
                    "Regenerate with strictly grounded claims only.",
                ],
                "retryable": True,
            },
        }

        def fake_send(_, model, temperature, response_format=None, **kwargs):
            payload = stage_payloads[response_format.__name__]
            return payload, 11, {
                "input_tokens": 4,
                "output_tokens": 7,
                "total_tokens": 11,
                "resolved_total_tokens": 11,
            }

        with patch("core.pipeline.run_analysis.send_ultragpt_chat", side_effect=fake_send):
            result = run_analysis(
                raw_text=(
                    "Scene\n"
                    "Riya receives a message from her ex-boyfriend after five years.\n"
                    "Dialogue\n"
                    "Riya: Why now?\n"
                    "Arjun: Because today I learned the truth.\n"
                    "Riya: What truth?\n"
                    "Arjun: That the accident wasn't your fault."
                ),
                title="The Last Message",
                config=AnalysisConfig(max_iterations=1),
            )

        self.assertIsNotNone(result.validation)
        self.assertFalse(result.validation.valid)
        self.assertEqual(result.iterations, 1)
        self.assertEqual(result.tokens_used, 55)
        self.assertIn("validation_1", result.step_details)

    def test_provider_counts_token_usage_metadata(self):
        msg = SimpleNamespace(
            usage_metadata=None,
            response_metadata={
                "token_usage": {
                    "prompt_tokens": 19,
                    "completion_tokens": 7,
                    "total_tokens": 26,
                }
            },
        )

        self.assertEqual(
            BaseOpenAICompatibleProvider._usage_total_tokens_from_message(msg),
            26,
        )


if __name__ == "__main__":
    unittest.main()
