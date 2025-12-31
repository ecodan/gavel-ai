"""
Base classes and interfaces for reporters.

Defines the Reporter ABC that all reporter implementations must inherit from.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from gavel_ai.telemetry import get_tracer

if TYPE_CHECKING:
    from gavel_ai.core.models import ReporterConfig


class Reporter(ABC):
    """
    Abstract base class for report generators.

    All reporter implementations must inherit from this class and implement
    the async generate() method.

    Per Architecture Decision 8: Domain-driven storage abstraction with clean interfaces.
    - Reporter takes config in constructor containing template and formatting rules
    - Reporter handles its own template rendering (implementation chooses mechanism)
    - Reporter emits OpenTelemetry spans internally
    """

    def __init__(self, config: "ReporterConfig"):  # type: ignore
        """
        Initialize reporter with configuration.

        Args:
            config: ReporterConfig instance with reporter behavioral rules
        """
        from gavel_ai.core.models import ReporterConfig

        self.config: ReporterConfig = config
        self.tracer = get_tracer(__name__)

    @abstractmethod
    async def generate(self, run: Any, template: str) -> str:
        """
        Generate report from run data and template.

        Args:
            run: Run instance containing evaluation results and metadata
            template: Template name or path to use for report generation

        Returns:
            str: Generated report content (HTML, Markdown, or other format)

        Raises:
            ReporterError: On template loading or rendering failures
        """
        pass
