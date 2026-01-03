"""
Judge registry and factory for gavel-ai.

Provides centralized registration and instantiation of judge implementations.
Per Epic 4 Story 4.4: Registry pattern for pluggable judge discovery.
"""

from typing import Dict, Type

from gavel_ai.core.exceptions import JudgeError
from gavel_ai.core.models import JudgeConfig
from gavel_ai.judges.base import Judge


class JudgeRegistry:
    """
    Registry for judge implementations.

    Allows judges to be registered and instantiated by type name without
    modifying core code.
    """

    _registry: Dict[str, Type[Judge]] = {}

    @classmethod
    def register(cls, judge_type: str, judge_class: Type[Judge]) -> None:
        """
        Register a judge implementation.

        Args:
            judge_type: The judge type identifier (e.g., "deepeval.similarity")
            judge_class: The Judge class implementation

        Raises:
            JudgeError: If judge_type is already registered
        """
        if judge_type in cls._registry:
            raise JudgeError(
                f"Judge type '{judge_type}' is already registered - "
                f"Cannot register multiple implementations for the same type"
            )
        cls._registry[judge_type] = judge_class

    @classmethod
    def create(cls, config: JudgeConfig) -> Judge:
        """
        Create a judge instance from configuration.

        Args:
            config: JudgeConfig specifying the judge type and parameters

        Returns:
            Instantiated Judge implementation

        Raises:
            JudgeError: If judge type is not found in registry
        """
        judge_type = config.type

        if judge_type not in cls._registry:
            available = ", ".join(sorted(cls._registry.keys()))
            raise JudgeError(
                f"Judge type '{judge_type}' not found in registry - "
                f"Available types: {available if available else 'none'}"
            )

        judge_class = cls._registry[judge_type]
        return judge_class(config)

    @classmethod
    def list_available(cls) -> list[str]:
        """
        List all registered judge types.

        Returns:
            Sorted list of available judge type identifiers
        """
        return sorted(cls._registry.keys())

    @classmethod
    def clear(cls) -> None:
        """
        Clear all registered judges.

        Primarily for testing purposes.
        """
        cls._registry.clear()
