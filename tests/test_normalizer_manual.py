import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from ultraprint.logging import logger

from core.config import log_config
from core.services.normalizer import normalize_script_input


log = logger("llm_log", **log_config)


def run_case(
    name: str,
    raw_text: str,
    expected_format: str | None = None,
    expected_characters: list[str] | None = None,
    expected_line_count: int | None = None,
) -> None:
    log.info("=== %s ===", name)
    try:
        result = normalize_script_input(raw_text)
    except Exception as exc:
        log.error("ERROR: %s", exc)
        return

    log.info("format: %s", result.script_format)
    log.info("characters: %s", result.detected_characters)
    log.info("line_count: %s", len(result.line_map))
    log.info("line_map: %s", result.line_map)

    issues: list[str] = []
    if expected_format and result.script_format != expected_format:
        issues.append(f"format expected {expected_format}, got {result.script_format}")
    if expected_characters is not None and result.detected_characters != expected_characters:
        issues.append(
            f"characters expected {expected_characters}, got {result.detected_characters}"
        )
    if expected_line_count is not None and len(result.line_map) != expected_line_count:
        issues.append(
            f"line_count expected {expected_line_count}, got {len(result.line_map)}"
        )

    if issues:
        log.warning("FAIL:")
        for issue in issues:
            log.warning("- %s", issue)
    else:
        log.info("PASS")


def run_error_case(name: str, raw_text) -> None:
    log.info("=== %s ===", name)
    try:
        normalize_script_input(raw_text)
    except Exception as exc:
        log.info("PASS (error as expected): %s", exc)
        return
    log.warning("FAIL: expected an error but none was raised")


def main() -> None:
    run_case(
        "basic_dialogue",
        "Riya: Why now?\nArjun: Because today I learned the truth.",
        expected_format="dialogue",
        expected_characters=["Riya", "Arjun"],
        expected_line_count=2,
    )

    run_case(
        "scene_and_dialogue",
        "INT. ROOM - NIGHT\nRiya: Why now?\nArjun: Because today I learned the truth.",
        expected_format="scene_dialogue",
        expected_characters=["Riya", "Arjun"],
        expected_line_count=3,
    )

    run_case(
        "scene_only",
        "EXT. PARK - DAY\nSCENE 2",
        expected_format="mixed",
        expected_characters=[],
        expected_line_count=2,
    )

    run_case(
        "empty_string",
        "",
        expected_format="unknown",
        expected_characters=[],
        expected_line_count=0,
    )

    run_case(
        "blank_lines_and_whitespace",
        "  Riya:  Why now?  \n\n  Arjun:  Because today I learned the truth.  ",
        expected_format="dialogue",
        expected_characters=["Riya", "Arjun"],
        expected_line_count=3,
    )

    run_case(
        "parenthetical_names",
        "RIYA (V.O.): I remember.\nARJUN (O.S.): Me too.",
        expected_format="dialogue",
        expected_characters=["Riya", "Arjun"],
        expected_line_count=2,
    )

    run_case(
        "assignment_example",
        "Title: The Last Message\nScene\nRiya: Why now?\nArjun: Because today I learned the truth.\nRiya: What truth?\nArjun: That the accident wasn't your fault.",
        expected_format="scene_dialogue",
        expected_characters=["Riya", "Arjun"],
        expected_line_count=6,
    )

    run_case(
        "tabs_and_spaces",
        "\tRiya:\tWhy now?\n\tArjun:\tBecause today I learned the truth.",
        expected_format="dialogue",
        expected_characters=["Riya", "Arjun"],
        expected_line_count=2,
    )

    run_case(
        "multi_word_names",
        "OLD MAN: Get off my lawn.\nYOUNG GIRL: Sorry.",
        expected_format="dialogue",
        expected_characters=["Old Man", "Young Girl"],
        expected_line_count=2,
    )

    run_case(
        "numbers_and_hyphen_names",
        "AGENT-47: Move.\nUNIT 7: Copy.",
        expected_format="dialogue",
        expected_characters=["Agent-47", "Unit 7"],
        expected_line_count=2,
    )

    run_case(
        "lowercase_scene_heading",
        "int. room - night",
        expected_format="mixed",
        expected_characters=[],
        expected_line_count=1,
    )

    run_case(
        "colon_non_dialogue",
        "Location: Park\nTime: Night",
        expected_format="dialogue",
        expected_characters=["Location", "Time"],
        expected_line_count=2,
    )

    run_case(
        "random_unstructured",
        "this is just random text\nwith no clear structure\nand no dialogue markers",
        expected_format="unknown",
        expected_characters=[],
        expected_line_count=3,
    )

    run_error_case("none_input", None)


if __name__ == "__main__":
    main()
