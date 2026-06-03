"""
Workflow execution framework for gavel-ai.

Provides:
- EvalContext: Immutable container for evaluation metadata (configs, scenarios, prompts)
- RunContext: Mutable container for run state (step outputs, artifacts)
- Step ABC: Abstract base class for workflow phases
- StepPhase: Enum identifying workflow phases

Per Tech Spec 3.9: Refactors OneShot run() into clean, testable architecture.
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ConfigError, RunPolicyError, ValidationError
from gavel_ai.core.issue_classifier import classify
from gavel_ai.models.config import ErrorPolicy
from gavel_ai.telemetry import get_tracer

DEFAULT_EVAL_ROOT: str = ".gavel/evaluations"


class StepPhase(Enum):
    """Workflow step phases in execution order."""

    PREPARE = "prepare"
    VALIDATION = "validation"
    SCENARIO_PROCESSING = "scenario_processing"
    JUDGING = "judging"
    REPORTING = "reporting"


class Step(ABC):
    """
    Abstract step in the OneShot workflow.

    Steps are isolated units of execution that:
    - Read inputs from RunContext.eval_ctx (via DataSources)
    - Write outputs to RunContext artifact DataSources
    - Log progress using run_ctx.run_logger
    - Use tracer for observability
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize step.

        Args:
            logger: Logger for step execution (class-level logging)
        """
        self.logger: logging.Logger = logger
        self.tracer = get_tracer(__name__)

    @property
    @abstractmethod
    def phase(self) -> StepPhase:
        """Which phase of the workflow this step executes in."""
        pass

    @abstractmethod
    async def execute(self, context: RunContext) -> None:
        """
        Execute the step.

        Args:
            context: RunContext for reading inputs and writing outputs

        Raises:
            ValidationError: On validation failures (terminal by default)
            ConfigError: On configuration issues (terminal by default)
            Exception: Other errors propagate as terminal by default

        Implementation notes:
        - Read inputs via: context.eval_ctx.eval_config.read()
        - Write outputs via: context.results_raw.append(record)
        - Log progress using: context.run_logger.info("message")
        - Use tracer.start_as_current_span() for observability
        """
        pass

    async def safe_execute(
        self, context: RunContext, error_policy: Optional[ErrorPolicy] = None
    ) -> bool:
        """
        Execute with error handling wrapper.

        Called by workflow orchestrator. Classifies exceptions via IssueClassifier
        and respects the eval's ErrorPolicy (exit_on_error / exit_on_warning).

        Returns:
            True if successful, False on terminal error
        Raises:
            RunPolicyError: immediately when a classified tier exceeds policy
        """
        policy = error_policy or ErrorPolicy()
        try:
            await self.execute(context)
            context.mark_step_complete(self.phase)
            return True
        except RunPolicyError:
            raise
        except Exception as e:
            tier = classify(e)
            log_msg = f"{self.phase.value} failed [{tier}]: {e}"
            if tier == "WARNING":
                self.logger.warning(log_msg)
                context.run_logger.warning(log_msg, exc_info=True)
            else:
                self.logger.error(log_msg)
                context.run_logger.error(log_msg, exc_info=True)
            context.last_step_error = e

            if policy.should_halt(tier):
                raise RunPolicyError(log_msg, tier=tier, cause=e) from e
            return False


class ValidationResult:
    """Result from validation step."""

    def __init__(
        self,
        is_valid: bool,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.is_valid: bool = is_valid
        self.errors: List[str] = errors or []
        self.warnings: List[str] = warnings or []
