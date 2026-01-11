"""Agent configuration schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelDefinition(BaseModel):
    """Shared model definition for provider configuration."""

    model_config = ConfigDict(extra="ignore")

    model_provider: str
    model_family: str
    model_version: str
    model_parameters: Dict[str, Any]
    provider_auth: Dict[str, Any]


class AgentConfig(BaseModel):
    """Agent configuration referencing a model."""

    model_config = ConfigDict(extra="ignore")

    model_id: str
    prompt: str
    model_parameters: Optional[Dict[str, Any]] = None
    custom_configs: Optional[Dict[str, Any]] = None


class AgentsFile(BaseModel):
    """Complete agents.json structure with models and agents."""

    model_config = ConfigDict(extra="allow")

    # Required _models section
    models: Dict[str, ModelDefinition] = Field(alias="_models")

    @property
    def _models(self) -> Dict[str, ModelDefinition]:
        """Alias for models to match JSON format."""
        return self.models
