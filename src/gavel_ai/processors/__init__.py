"""
Processors module for gavel-ai.

Input processors for different evaluation modes.

This module provides the InputProcessor base class and implementations for PromptInput,
ExternalHttp, and Scenario processors.

"""

from gavel_ai.processors.base import InputProcessor
from gavel_ai.processors.external_http_processor import ExternalHttpProcessor
from gavel_ai.processors.prompt_processor import PromptInputProcessor
from gavel_ai.processors.scenario_processor import ScenarioProcessor

# Export public API
__all__ = [
    "InputProcessor",
    "PromptInputProcessor",
    "ExternalHttpProcessor",
    "ScenarioProcessor",
]
