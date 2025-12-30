"""
Judges module for gavel-ai.

Judge implementations for LLM evaluation.

This module contains the Judge base class and DeepEval integration for scoring LLM outputs.
Per Architecture Decision 5: DeepEval-native judges with sequential execution.
"""

from gavel_ai.judges.base import Judge
from gavel_ai.judges.deepeval_judge import DeepEvalJudge
from gavel_ai.judges.judge_executor import JudgeExecutor
from gavel_ai.judges.judge_registry import JudgeRegistry
from gavel_ai.judges.rejudge import ReJudge


def _register_default_judges() -> None:
    """Register default judge implementations with the registry."""
    # Register DeepEvalJudge for all supported DeepEval types
    for judge_type in DeepEvalJudge.JUDGE_TYPE_MAP.keys():
        JudgeRegistry.register(judge_type, DeepEvalJudge)


# Auto-register judges on module import
_register_default_judges()

# Export public API
__all__ = ["Judge", "DeepEvalJudge", "JudgeRegistry", "JudgeExecutor", "ReJudge"]
