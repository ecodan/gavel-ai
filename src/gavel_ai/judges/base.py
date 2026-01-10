"""
Judge base class and interface for gavel-ai.

Defines the abstract Judge interface that all judge implementations must follow.
Per Architecture Decision 5: DeepEval-native judges with sequential execution.
"""

from abc import ABC, abstractmethod
from typing import Optional

from gavel_ai.core.models import JudgeConfig, JudgeResult, Scenario
from gavel_ai.telemetry import get_tracer


class Judge(ABC):
    """
    Abstract base class for judges.

    Per Epic 4 Story 4.1: All judges must implement the evaluate() method
    and produce JudgeResult with score (1-10), reasoning, and evidence.

    Judges evaluate processor outputs against scenarios and expected behavior,
    producing scored results that enable variant comparison.
    """

    def __init__(self, config: JudgeConfig):
        """
        Initialize judge with configuration.

        Args:
            config: JudgeConfig instance with judge type, threshold, and settings
        """
        self.config = config
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def evaluate(self, scenario: Scenario, subject_output: str) -> JudgeResult:
        """
        Evaluate a subject's output against a scenario.

        Args:
            scenario: The test scenario with input and expected behavior
            subject_output: The output from the processor/system being evaluated

        Returns:
            JudgeResult with score (1-10), optional reasoning, and optional evidence

        Raises:
            JudgeError: On evaluation failures
        """
        pass
