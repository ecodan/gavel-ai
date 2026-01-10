import logging
from abc import ABCMeta, abstractmethod

from gavel_ai.core.contexts import EvalContext, RunContext


class GavelWorkflow(metaclass=ABCMeta):
    def __init__(self, eval_context: EvalContext, app_logger: logging.Logger) -> None:
        self.logger: logging.Logger = app_logger
        self.eval_context: EvalContext = eval_context

    @abstractmethod
    def execute(self) -> RunContext:
        """
        Execute OneShot workflow - orchestrates validator → processor → judge → reporter steps.

        Returns:
            RunContext with all step outputs populated

        Raises:
            ConfigError: If configuration is invalid
            ValidationError: If validation fails
        """
        pass
