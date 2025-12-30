"""
Base classes and interfaces for processors.

Defines the InputProcessor ABC that all processor implementations must inherit from.
"""

from abc import ABC, abstractmethod
from typing import List

from gavel_ai.core.models import Input, ProcessorConfig, ProcessorResult
from gavel_ai.telemetry import get_tracer


class InputProcessor(ABC):
    """
    Abstract base class for input processors.

    All processor implementations must inherit from this class and implement
    the async process() method.

    Per Architecture Decision 3: Config-driven design with per-processor batching.
    - Processor takes config in constructor containing behavioral rules
    - Processor handles its own batching (implementation chooses mechanism)
    - Processor emits OpenTelemetry spans internally
    """

    def __init__(self, config: ProcessorConfig):
        """
        Initialize processor with configuration.

        Args:
            config: ProcessorConfig instance with processor behavioral rules
        """
        self.config = config
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def process(self, inputs: List[Input]) -> ProcessorResult:
        """
        Execute processor against batch of inputs.

        Args:
            inputs: List of Input instances to process

        Returns:
            ProcessorResult with output, metadata, and optional error

        Raises:
            ProcessorError: On execution failures
        """
        pass
