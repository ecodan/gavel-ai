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
    with tracer.start_as_current_span("judges.load_judge_config"):
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
            id=judge.id,
            deepeval_name=judge.deepeval_name,
            config=merged_config,
            config_ref=judge.config_ref,
        )


def validate_judge_ids(judges: List[JudgeConfig]) -> None:
    """Validate judge IDs are unique.

    Args:
        judges: List of judge configurations

    Raises:
        JudgeError: If duplicate judge IDs found
    """
    with tracer.start_as_current_span("judges.validate_judge_ids"):
        judge_ids = [j.id for j in judges]
        seen = set()
        duplicates = []

        for judge_id in judge_ids:
            if judge_id in seen:
                duplicates.append(judge_id)
            seen.add(judge_id)

        if duplicates:
            raise JudgeError(
                f"Duplicate judge IDs found: {', '.join(duplicates)} - "
                f"Judge IDs must be unique"
            )


def validate_deepeval_name(deepeval_name: str) -> None:
    """Validate deepeval judge type is supported.

    Args:
        deepeval_name: DeepEval judge type name

    Raises:
        JudgeError: If deepeval_name not supported
    """
    if deepeval_name not in SUPPORTED_DEEPEVAL_JUDGES:
        supported_list = ", ".join(sorted(SUPPORTED_DEEPEVAL_JUDGES))
        raise JudgeError(
            f"Unsupported deepeval judge: {deepeval_name} - "
            f"Supported judges: {supported_list}"
        )
