"""Unit tests for agents configuration schema."""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from gavel_ai.core.config import load_config
from gavel_ai.core.config.agents import (
    AgentConfig,
    AgentsFile,
    ModelDefinition,
    merge_parameters,
    validate_agent_references,
)
from gavel_ai.core.exceptions import ConfigError


class TestModelDefinition:
    """Test suite for ModelDefinition Pydantic model."""

    def test_parse_anthropic_model(self) -> None:
        """Test parsing Anthropic model definition."""
        model_data: Dict[str, Any] = {
            "model_provider": "anthropic",
            "model_family": "claude",
            "model_version": "claude-sonnet-4-5-latest",
            "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
            "provider_auth": {"api_key": "sk-ant-test"},
        }

        model = ModelDefinition.model_validate(model_data)

        assert model.model_provider == "anthropic"
        assert model.model_family == "claude"
        assert model.model_version == "claude-sonnet-4-5-latest"
        assert model.model_parameters["temperature"] == 0.7

    def test_parse_openai_model(self) -> None:
        """Test parsing OpenAI model definition."""
        model_data: Dict[str, Any] = {
            "model_provider": "openai",
            "model_family": "gpt",
            "model_version": "gpt-4o",
            "model_parameters": {"temperature": 0.8, "max_tokens": 2048},
            "provider_auth": {"api_key": "sk-openai-test"},
        }

        model = ModelDefinition.model_validate(model_data)

        assert model.model_provider == "openai"
        assert model.model_family == "gpt"
        assert model.model_version == "gpt-4o"

    def test_parse_ollama_model(self) -> None:
        """Test parsing Ollama model definition."""
        model_data: Dict[str, Any] = {
            "model_provider": "ollama",
            "model_family": "qwen",
            "model_version": "qwen",
            "model_parameters": {"temperature": 0.7},
            "provider_auth": {"base_url": "http://localhost:11434"},
        }

        model = ModelDefinition.model_validate(model_data)

        assert model.model_provider == "ollama"
        assert model.provider_auth["base_url"] == "http://localhost:11434"

    def test_model_definition_has_extra_ignore(self) -> None:
        """Test that ModelDefinition ignores unknown fields."""
        model_data: Dict[str, Any] = {
            "model_provider": "anthropic",
            "model_family": "claude",
            "model_version": "claude-sonnet-4-5-latest",
            "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
            "provider_auth": {"api_key": "sk-ant-test"},
            "future_field": "should_be_ignored",
        }

        model = ModelDefinition.model_validate(model_data)

        assert model.model_provider == "anthropic"
        assert not hasattr(model, "future_field")


class TestAgentConfig:
    """Test suite for AgentConfig Pydantic model."""

    def test_parse_agent_with_model_id(self) -> None:
        """Test parsing agent config with model_id reference."""
        agent_data: Dict[str, Any] = {
            "model_id": "claude-standard",
            "prompt": "assistant:v1",
        }

        agent = AgentConfig.model_validate(agent_data)

        assert agent.model_id == "claude-standard"
        assert agent.prompt == "assistant:v1"
        assert agent.model_parameters is None

    def test_parse_agent_with_parameter_override(self) -> None:
        """Test parsing agent with parameter overrides."""
        agent_data: Dict[str, Any] = {
            "model_id": "claude-standard",
            "prompt": "assistant:v1",
            "model_parameters": {"temperature": 0.3},
        }

        agent = AgentConfig.model_validate(agent_data)

        assert agent.model_id == "claude-standard"
        assert agent.model_parameters == {"temperature": 0.3}

    def test_parse_agent_with_custom_configs(self) -> None:
        """Test parsing agent with custom configs."""
        agent_data: Dict[str, Any] = {
            "model_id": "claude-standard",
            "prompt": "assistant:v1",
            "custom_configs": {"logging": {"enabled": True}},
        }

        agent = AgentConfig.model_validate(agent_data)

        assert agent.custom_configs == {"logging": {"enabled": True}}

    def test_agent_config_has_extra_ignore(self) -> None:
        """Test that AgentConfig ignores unknown fields."""
        agent_data: Dict[str, Any] = {
            "model_id": "claude-standard",
            "prompt": "assistant:v1",
            "future_option": "ignored",
        }

        agent = AgentConfig.model_validate(agent_data)

        assert agent.model_id == "claude-standard"
        assert not hasattr(agent, "future_option")


class TestAgentsFile:
    """Test suite for AgentsFile Pydantic model."""

    def test_parse_complete_agents_file(self, tmp_path: Path) -> None:
        """Test parsing complete agents.json structure."""
        agents_data: Dict[str, Any] = {
            "_models": {
                "claude-standard": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-sonnet-4-5-latest",
                    "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                    "provider_auth": {"api_key": "sk-ant-test"},
                },
                "gpt-standard": {
                    "model_provider": "openai",
                    "model_family": "gpt",
                    "model_version": "gpt-4o",
                    "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                    "provider_auth": {"api_key": "sk-openai-test"},
                },
            },
            "subject_agent": {"model_id": "claude-standard", "prompt": "assistant:v1"},
            "baseline_agent": {"model_id": "gpt-standard", "prompt": "assistant:v1"},
        }

        agents_file = tmp_path / "agents.json"
        with open(agents_file, "w") as f:
            json.dump(agents_data, f)

        agents = load_config(agents_file, AgentsFile)

        assert len(agents._models) == 2
        assert "claude-standard" in agents._models
        assert "gpt-standard" in agents._models

    def test_get_agent_by_name(self, tmp_path: Path) -> None:
        """Test retrieving agent config by name."""
        agents_data: Dict[str, Any] = {
            "_models": {
                "claude-standard": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-sonnet-4-5-latest",
                    "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                    "provider_auth": {"api_key": "sk-ant-test"},
                }
            },
            "subject_agent": {"model_id": "claude-standard", "prompt": "assistant:v1"},
        }

        agents_file = tmp_path / "agents.json"
        with open(agents_file, "w") as f:
            json.dump(agents_data, f)

        agents = load_config(agents_file, AgentsFile)
        agent = agents.get_agent("subject_agent")

        assert agent.model_id == "claude-standard"
        assert agent.prompt == "assistant:v1"

    def test_get_nonexistent_agent_raises_error(self, tmp_path: Path) -> None:
        """Test that getting nonexistent agent raises ConfigError."""
        agents_data: Dict[str, Any] = {
            "_models": {
                "claude-standard": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-sonnet-4-5-latest",
                    "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                    "provider_auth": {"api_key": "sk-ant-test"},
                }
            },
            "subject_agent": {"model_id": "claude-standard", "prompt": "assistant:v1"},
        }

        agents_file = tmp_path / "agents.json"
        with open(agents_file, "w") as f:
            json.dump(agents_data, f)

        agents = load_config(agents_file, AgentsFile)

        with pytest.raises(ConfigError) as exc_info:
            agents.get_agent("nonexistent_agent")

        assert "not found" in str(exc_info.value).lower()


class TestModelLinking:
    """Test suite for model linking validation."""

    def test_validate_agent_references_success(self, tmp_path: Path) -> None:
        """Test successful validation when all model_id references exist."""
        agents_data: Dict[str, Any] = {
            "_models": {
                "claude-standard": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-sonnet-4-5-latest",
                    "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                    "provider_auth": {"api_key": "sk-ant-test"},
                }
            },
            "subject_agent": {"model_id": "claude-standard", "prompt": "assistant:v1"},
        }

        agents_file = tmp_path / "agents.json"
        with open(agents_file, "w") as f:
            json.dump(agents_data, f)

        agents = load_config(agents_file, AgentsFile)

        # Should not raise exception
        validate_agent_references(agents)

    def test_validate_agent_references_missing_model_id(self, tmp_path: Path) -> None:
        """Test validation fails when model_id reference doesn't exist."""
        agents_data: Dict[str, Any] = {
            "_models": {
                "claude-standard": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-sonnet-4-5-latest",
                    "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                    "provider_auth": {"api_key": "sk-ant-test"},
                }
            },
            "subject_agent": {
                "model_id": "nonexistent-model",  # Invalid reference
                "prompt": "assistant:v1",
            },
        }

        agents_file = tmp_path / "agents.json"
        with open(agents_file, "w") as f:
            json.dump(agents_data, f)

        agents = load_config(agents_file, AgentsFile)

        with pytest.raises(ConfigError) as exc_info:
            validate_agent_references(agents)

        error_msg = str(exc_info.value)
        assert "nonexistent-model" in error_msg
        assert "model_id" in error_msg.lower() or "unknown" in error_msg.lower()


class TestParameterMerging:
    """Test suite for parameter override logic."""

    def test_merge_parameters_no_override(self) -> None:
        """Test merging when agent has no parameter overrides."""
        model_def = ModelDefinition.model_validate(
            {
                "model_provider": "anthropic",
                "model_family": "claude",
                "model_version": "claude-sonnet-4-5-latest",
                "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                "provider_auth": {"api_key": "sk-ant-test"},
            }
        )

        agent_config = AgentConfig.model_validate(
            {"model_id": "claude-standard", "prompt": "assistant:v1"}
        )

        merged = merge_parameters(model_def, agent_config)

        assert merged["temperature"] == 0.7
        assert merged["max_tokens"] == 4096

    def test_merge_parameters_with_override(self) -> None:
        """Test merging when agent overrides some parameters."""
        model_def = ModelDefinition.model_validate(
            {
                "model_provider": "anthropic",
                "model_family": "claude",
                "model_version": "claude-sonnet-4-5-latest",
                "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                "provider_auth": {"api_key": "sk-ant-test"},
            }
        )

        agent_config = AgentConfig.model_validate(
            {
                "model_id": "claude-standard",
                "prompt": "assistant:v1",
                "model_parameters": {"temperature": 0.3},  # Override
            }
        )

        merged = merge_parameters(model_def, agent_config)

        assert merged["temperature"] == 0.3  # Overridden
        assert merged["max_tokens"] == 4096  # Kept from model

    def test_merge_parameters_agent_adds_new_param(self) -> None:
        """Test merging when agent adds new parameters."""
        model_def = ModelDefinition.model_validate(
            {
                "model_provider": "anthropic",
                "model_family": "claude",
                "model_version": "claude-sonnet-4-5-latest",
                "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
                "provider_auth": {"api_key": "sk-ant-test"},
            }
        )

        agent_config = AgentConfig.model_validate(
            {
                "model_id": "claude-standard",
                "prompt": "assistant:v1",
                "model_parameters": {"top_p": 0.9},  # New param
            }
        )

        merged = merge_parameters(model_def, agent_config)

        assert merged["temperature"] == 0.7  # From model
        assert merged["max_tokens"] == 4096  # From model
        assert merged["top_p"] == 0.9  # Added by agent


class TestProviderTypes:
    """Test suite for all supported provider types."""

    def test_anthropic_provider(self) -> None:
        """Test Anthropic provider configuration."""
        model_data: Dict[str, Any] = {
            "model_provider": "anthropic",
            "model_family": "claude",
            "model_version": "claude-sonnet-4-5-latest",
            "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
            "provider_auth": {"api_key": "{{ANTHROPIC_API_KEY}}"},
        }

        model = ModelDefinition.model_validate(model_data)

        assert model.model_provider == "anthropic"
        assert model.provider_auth["api_key"] == "{{ANTHROPIC_API_KEY}}"

    def test_openai_provider(self) -> None:
        """Test OpenAI provider configuration."""
        model_data: Dict[str, Any] = {
            "model_provider": "openai",
            "model_family": "gpt",
            "model_version": "gpt-4o",
            "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
            "provider_auth": {"api_key": "{{OPENAI_API_KEY}}"},
        }

        model = ModelDefinition.model_validate(model_data)

        assert model.model_provider == "openai"

    def test_google_provider(self) -> None:
        """Test Google provider configuration."""
        model_data: Dict[str, Any] = {
            "model_provider": "google",
            "model_family": "gemini",
            "model_version": "gemini-1.5-pro",
            "model_parameters": {"temperature": 0.7, "max_tokens": 4096},
            "provider_auth": {"api_key": "{{GOOGLE_API_KEY}}"},
        }

        model = ModelDefinition.model_validate(model_data)

        assert model.model_provider == "google"
        assert model.model_family == "gemini"

    def test_ollama_provider(self) -> None:
        """Test Ollama provider configuration (local)."""
        model_data: Dict[str, Any] = {
            "model_provider": "ollama",
            "model_family": "qwen",
            "model_version": "qwen",
            "model_parameters": {"temperature": 0.7},
            "provider_auth": {"base_url": "http://localhost:11434"},
        }

        model = ModelDefinition.model_validate(model_data)

        assert model.model_provider == "ollama"
        assert "base_url" in model.provider_auth
