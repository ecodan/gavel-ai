"""
Unit tests for agent models.
"""

import pytest
from pydantic import ValidationError

from gavel_ai.models.agents import AgentConfig, AgentsFile, ModelDefinition


class TestModelDefinition:
    """Test ModelDefinition model."""

    def test_model_definition_basic_creation(self):
        """ModelDefinition can be created with required fields."""
        model = ModelDefinition(
            model_provider="anthropic",
            model_family="claude",
            model_version="claude-4-5-sonnet-latest",
            model_parameters={"temperature": 0.7},
            provider_auth={"api_key": "sk-test"},
        )
        assert model.model_provider == "anthropic"
        assert model.model_family == "claude"
        assert model.model_version == "claude-4-5-sonnet-latest"
        assert model.model_parameters == {"temperature": 0.7}
        assert model.provider_auth == {"api_key": "sk-test"}

    def test_model_definition_all_fields(self):
        """ModelDefinition stores all fields correctly."""
        model = ModelDefinition(
            model_provider="openai",
            model_family="gpt",
            model_version="gpt-4",
            model_parameters={"temperature": 0.9, "max_tokens": 4096},
            provider_auth={"api_key": "sk-openai", "base_url": "https://api.openai.com"},
        )
        assert model.model_provider == "openai"
        assert model.model_family == "gpt"
        assert model.model_parameters["temperature"] == 0.9
        assert model.model_parameters["max_tokens"] == 4096

    def test_model_definition_extra_ignore(self):
        """ModelDefinition ignores extra fields."""
        model_dict = {
            "model_provider": "anthropic",
            "model_family": "claude",
            "model_version": "claude-4-5-sonnet-latest",
            "model_parameters": {},
            "provider_auth": {},
            "extra_field": "ignored",
        }
        model = ModelDefinition(**model_dict)
        assert not hasattr(model, "extra_field")

    def test_model_definition_requires_model_provider(self):
        """ModelDefinition requires model_provider field."""
        with pytest.raises(ValidationError):
            ModelDefinition(
                model_family="claude",
                model_version="claude-4-5-sonnet-latest",
                model_parameters={},
                provider_auth={},
            )

    def test_model_definition_requires_model_family(self):
        """ModelDefinition requires model_family field."""
        with pytest.raises(ValidationError):
            ModelDefinition(
                model_provider="anthropic",
                model_version="claude-4-5-sonnet-latest",
                model_parameters={},
                provider_auth={},
            )

    def test_model_definition_requires_model_version(self):
        """ModelDefinition requires model_version field."""
        with pytest.raises(ValidationError):
            ModelDefinition(
                model_provider="anthropic",
                model_family="claude",
                model_parameters={},
                provider_auth={},
            )

    def test_model_definition_requires_model_parameters(self):
        """ModelDefinition requires model_parameters field."""
        with pytest.raises(ValidationError):
            ModelDefinition(
                model_provider="anthropic",
                model_family="claude",
                model_version="claude-4-5-sonnet-latest",
                provider_auth={},
            )

    def test_model_definition_requires_provider_auth(self):
        """ModelDefinition requires provider_auth field."""
        with pytest.raises(ValidationError):
            ModelDefinition(
                model_provider="anthropic",
                model_family="claude",
                model_version="claude-4-5-sonnet-latest",
                model_parameters={},
            )


class TestAgentConfig:
    """Test AgentConfig model."""

    def test_agent_config_basic_creation(self):
        """AgentConfig can be created with required fields."""
        agent = AgentConfig(
            model_id="claude-standard",
            prompt="assistant:v1",
        )
        assert agent.model_id == "claude-standard"
        assert agent.prompt == "assistant:v1"
        assert agent.model_parameters is None
        assert agent.custom_configs is None

    def test_agent_config_with_model_parameters(self):
        """AgentConfig can include model_parameters."""
        agent = AgentConfig(
            model_id="claude-standard",
            prompt="assistant:v1",
            model_parameters={"temperature": 0.5, "max_tokens": 2000},
        )
        assert agent.model_parameters["temperature"] == 0.5
        assert agent.model_parameters["max_tokens"] == 2000

    def test_agent_config_with_custom_configs(self):
        """AgentConfig can include custom_configs."""
        agent = AgentConfig(
            model_id="claude-standard",
            prompt="assistant:v1",
            custom_configs={"logging": {"enabled": True, "mode": "jsonl_file"}},
        )
        assert agent.custom_configs["logging"]["enabled"] is True
        assert agent.custom_configs["logging"]["mode"] == "jsonl_file"

    def test_agent_config_all_fields(self):
        """AgentConfig can include all optional fields."""
        agent = AgentConfig(
            model_id="claude-standard",
            prompt="assistant:v1",
            model_parameters={"temperature": 0.7},
            custom_configs={"key": "value"},
        )
        assert agent.model_id == "claude-standard"
        assert agent.prompt == "assistant:v1"
        assert agent.model_parameters is not None
        assert agent.custom_configs is not None

    def test_agent_config_extra_ignore(self):
        """AgentConfig ignores extra fields."""
        agent_dict = {
            "model_id": "claude-standard",
            "prompt": "assistant:v1",
            "extra_field": "ignored",
        }
        agent = AgentConfig(**agent_dict)
        assert not hasattr(agent, "extra_field")

    def test_agent_config_requires_model_id(self):
        """AgentConfig requires model_id field."""
        with pytest.raises(ValidationError):
            AgentConfig(prompt="assistant:v1")

    def test_agent_config_requires_prompt(self):
        """AgentConfig requires prompt field."""
        with pytest.raises(ValidationError):
            AgentConfig(model_id="claude-standard")


class TestAgentsFile:
    """Test AgentsFile model."""

    def test_agents_file_basic_creation(self):
        """AgentsFile can be created with _models section."""
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
        assert "claude-standard" in agents_file.models

    def test_agents_file_multiple_models(self):
        """AgentsFile can contain multiple models."""
        agents_file = AgentsFile(
            _models={
                "claude-standard": ModelDefinition(
                    model_provider="anthropic",
                    model_family="claude",
                    model_version="claude-4-5-sonnet-latest",
                    model_parameters={},
                    provider_auth={},
                ),
                "gpt-standard": ModelDefinition(
                    model_provider="openai",
                    model_family="gpt",
                    model_version="gpt-4",
                    model_parameters={},
                    provider_auth={},
                ),
            },
        )
        assert len(agents_file.models) == 2
        assert "claude-standard" in agents_file.models
        assert "gpt-standard" in agents_file.models

    def test_agents_file_with_alias(self):
        """AgentsFile accepts '_models' alias."""
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
        assert "claude-standard" in agents_file.models

    def test_agents_file_extra_allow(self):
        """AgentsFile allows extra fields for agent definitions."""
        agents_file_dict = {
            "_models": {
                "claude-standard": ModelDefinition(
                    model_provider="anthropic",
                    model_family="claude",
                    model_version="claude-4-5-sonnet-latest",
                    model_parameters={},
                    provider_auth={},
                ),
            },
            "research_assistant": {
                "model_id": "claude-standard",
                "prompt": "research:v1",
            },
        }
        agents_file = AgentsFile(**agents_file_dict)
        # Extra fields in Pydantic v2 are stored in __pydantic_extra__
        assert "research_assistant" in agents_file.__pydantic_extra__

    def test_agents_file_requires_models(self):
        """AgentsFile requires _models section."""
        with pytest.raises(ValidationError):
            AgentsFile()

    def test_agents_file_models_property(self):
        """AgentsFile._models property returns models dict."""
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
        assert agents_file._models == agents_file.models

    def test_agents_file_empty_models(self):
        """AgentsFile can have empty _models dict."""
        agents_file = AgentsFile(_models={})
        assert agents_file.models == {}

    def test_agents_file_with_complex_extra_fields(self):
        """AgentsFile can handle complex extra field structures."""
        agents_file_dict = {
            "_models": {
                "claude-standard": ModelDefinition(
                    model_provider="anthropic",
                    model_family="claude",
                    model_version="claude-4-5-sonnet-latest",
                    model_parameters={},
                    provider_auth={},
                ),
            },
            "research_assistant": {
                "model_id": "claude-standard",
                "prompt": "research:v1",
                "model_parameters": {"temperature": 0.3},
                "custom_configs": {
                    "logging": {"enabled": True, "mode": "jsonl_file"},
                },
            },
        }
        agents_file = AgentsFile(**agents_file_dict)
        # Extra fields in Pydantic v2 are stored in __pydantic_extra__
        research_assistant = agents_file.__pydantic_extra__.get("research_assistant")
        assert research_assistant is not None
