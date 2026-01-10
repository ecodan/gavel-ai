"""Agents configuration schema with provider and model definitions."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.telemetry import get_tracer

tracer = get_tracer(__name__)


class ModelDefinition(BaseModel):
    """Shared model definition for provider configuration."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    model_provider: str  # "anthropic", "openai", "google", "ollama"
    model_family: str  # "claude", "gpt", "gemini", "qwen"
    model_version: str  # Specific model version
    model_parameters: Dict[str, Any]
    provider_auth: Dict[str, Any]


class AgentConfig(BaseModel):
    """Agent configuration referencing a model."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    model_id: str  # Reference to _models key
    prompt: str  # "prompt-name:version" format
    model_parameters: Optional[Dict[str, Any]] = None  # Override model params
    custom_configs: Optional[Dict[str, Any]] = None


class AgentsFile(BaseModel):
    """Complete agents.json structure with models and agents."""

    model_config = ConfigDict(extra="allow")  # Allow dynamic agent names

    # Required _models section
    models: Dict[str, ModelDefinition] = Field(alias="_models")

    def get_agent(self, agent_name: str) -> AgentConfig:
        """Get agent config by name.

        Args:
            agent_name: Name of the agent to retrieve

        Returns:
            AgentConfig for the requested agent

        Raises:
            ConfigError: If agent name not found
        """
        # Get raw dict for agent (stored as extra field)
        agent_dict = (
            self.__pydantic_extra__.get(agent_name) if hasattr(self, "__pydantic_extra__") else None
        )

        if agent_dict is None:
            raise ConfigError(
                f"Agent '{agent_name}' not found - Add agent definition to agents.json"
            )

        # Parse as AgentConfig
        return AgentConfig.model_validate(agent_dict)

    @property
    def _models(self) -> Dict[str, ModelDefinition]:
        """Alias for models to match JSON format."""
        return self.models


def validate_agent_references(agents_file: AgentsFile) -> None:
    """Validate all agent model_id references exist in _models.

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


def merge_parameters(
    model_def: ModelDefinition,
    agent_config: AgentConfig,
) -> Dict[str, Any]:
    """Merge agent parameters with model parameters.

    Agent-level parameters override model-level parameters.

    Args:
        model_def: Model definition with base parameters
        agent_config: Agent config with optional parameter overrides

    Returns:
        Merged parameter dictionary
    """
    # Start with model parameters
    params = model_def.model_parameters.copy()

    # Override with agent parameters
    if agent_config.model_parameters:
        params.update(agent_config.model_parameters)

    return params
