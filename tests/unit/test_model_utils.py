import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for model utility functions.
"""

import pytest

from gavel_ai.core.exceptions import ConfigError
from gavel_ai.models.agents import AgentsFile, ModelDefinition
from gavel_ai.models.utils import validate_agent_references


class TestValidateAgentReferences:
    """Test validate_agent_references function."""

    def test_validate_with_valid_references(self):
        """validate_agent_references passes when all model_ids are valid."""
        agents_file = AgentsFile(
            _models={
                "claude-standard": ModelDefinition(
                    model_provider="anthropic",
                    model_family="claude",
                    model_version="claude-4-5-sonnet-latest",
                    model_parameters={},
                    provider_auth={},
                ),
            },
        )
        agents_file.__pydantic_extra__ = {
            "agent1": {
                "model_id": "claude-standard",
                "prompt": "v1",
            },
        }

        validate_agent_references(agents_file)

    def test_validate_with_invalid_reference(self):
        """validate_agent_references raises ConfigError for invalid model_id."""
        agents_file = AgentsFile(
            _models={
                "claude-standard": ModelDefinition(
                    model_provider="anthropic",
                    model_family="claude",
                    model_version="claude-4-5-sonnet-latest",
                    model_parameters={},
                    provider_auth={},
                ),
            },
        )
        agents_file.__pydantic_extra__ = {
            "agent1": {
                "model_id": "non-existent-model",
                "prompt": "v1",
            },
        }

        with pytest.raises(ConfigError) as exc_info:
            validate_agent_references(agents_file)

        assert "agent1" in str(exc_info.value)
        assert "non-existent-model" in str(exc_info.value)

    def test_validate_with_no_model_id(self):
        """validate_agent_references ignores agents without model_id."""
        agents_file = AgentsFile(
            _models={
                "claude-standard": ModelDefinition(
                    model_provider="anthropic",
                    model_family="claude",
                    model_version="claude-4-5-sonnet-latest",
                    model_parameters={},
                    provider_auth={},
                ),
            },
        )
        agents_file.__pydantic_extra__ = {
            "agent_no_model": {
                "prompt": "v1",
            },
        }

        validate_agent_references(agents_file)

    def test_validate_with_empty_models(self):
        """validate_agent_references passes with no models."""
        agents_file = AgentsFile(_models={})
        validate_agent_references(agents_file)
