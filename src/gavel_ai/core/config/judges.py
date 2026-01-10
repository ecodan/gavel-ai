"""Judges configuration schema for DeepEval integration."""

import json
from pathlib import Path
from typing import List

from gavel_ai.core.config.models import JudgeConfig
from gavel_ai.core.exceptions import JudgeError
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)

# Supported DeepEval judge types
SUPPORTED_DEEPEVAL_JUDGES = {
    "deepeval.similarity",
    "deepeval.faithfulness",
    "deepeval.hallucination",
    "deepeval.answer_relevancy",
    "deepeval.contextual_precision",
    "deepeval.contextual_recall",
    "deepeval.geval",  # Custom GEval judge
}


def load_judge_config(judge: JudgeConfig, eval_root: Path) -> JudgeConfig:
    """Load judge config, merging external file if config_ref provided.

    Args:
        judge: Judge configuration
        eval_root: Evaluation root directory

    Returns:
        JudgeConfig with merged external config if applicable

    Raises:
        JudgeError: If config file not found
    """
    if not judge.config_ref:
        return judge

    # Load external config file
    config_file = eval_root / judge.config_ref
    if not config_file.exists():
        raise JudgeError(
            f"Judge config file not found: {judge.config_ref} - "
            f"Create file or fix config_ref path"
        )

    external_config = json.loads(config_file.read_text())

    # Merge configs (external overrides inline)
    merged_config = {**(judge.config or {}), **external_config}

    return JudgeConfig(
        name=judge.name,
        type=judge.type,
        config=merged_config,
        config_ref=judge.config_ref,
    )


def validate_judge_ids(judges: List[JudgeConfig]) -> None:
    """Validate judge names are unique.

    Args:
        judges: List of judge configurations

    Raises:
        JudgeError: If duplicate judge names found
    """
    judge_names = [j.name for j in judges]
    seen = set()
    duplicates = []

    for judge_name in judge_names:
        if judge_name in seen:
            duplicates.append(judge_name)
        seen.add(judge_name)

    if duplicates:
        raise JudgeError(
            f"Duplicate judge names found: {', '.join(duplicates)} - Judge names must be unique"
        )


def validate_judge_type(judge_type: str) -> None:
    """Validate judge type is supported.

    Args:
        judge_type: Judge type name

    Raises:
        JudgeError: If judge type not supported
    """
    if judge_type not in SUPPORTED_DEEPEVAL_JUDGES:
        supported_list = ", ".join(sorted(SUPPORTED_DEEPEVAL_JUDGES))
        raise JudgeError(
            f"Unsupported judge type: {judge_type} - Supported judges: {supported_list}"
        )
