"""
Utility functions for model validation.

This module contains validation helpers that are actively used throughout
the codebase. Unused validation functions have been removed to reduce
maintenance burden.

Functions:
- validate_agent_references(): Validates agent model_id references exist in _models
"""

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.models.agents import AgentsFile


def validate_agent_references(agents_file: AgentsFile) -> None:
    """
    Validate all agent model_id references exist in _models.

    Args:
        agents_file: Parsed AgentsFile instance

    Raises:
        ConfigError: If any agent references a non-existent model_id
    """
    # Get all extra fields (agent definitions)
    if not hasattr(agents_file, "__pydantic_extra__"):
        return

    for agent_name, agent_data in agents_file.__pydantic_extra__.items():
        if not isinstance(agent_data, dict):
            continue

        model_id = agent_data.get("model_id")
        if model_id and model_id not in agents_file._models:
            raise ConfigError(
                f"Agent '{agent_name}' references unknown model_id '{model_id}' - "
                f"Add '{model_id}' to _models section or fix model_id reference"
            )
