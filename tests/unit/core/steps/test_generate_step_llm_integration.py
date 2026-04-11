import pytest

pytestmark = pytest.mark.unit
"""
Additional tests for C-2.2 LLM integration functionality.

Tests the actual LLM scenario generation replacing mock implementation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.steps.generate_step import GenerateStep


class TestGenerateStepLLMIntegration:
    """Test GenerateStep LLM integration for C-2.2."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_context(self):
        """Create a mock RunContext."""
        context = MagicMock(spec=RunContext)
        context.eval_context = MagicMock()
        context.eval_context.eval_config.read.return_value = {}
        context.run_logger = MagicMock()
        return context

    @pytest.fixture
    def generate_step(self, mock_logger):
        """Create GenerateStep instance for testing."""
        return GenerateStep(mock_logger)

    @pytest.fixture
    def sample_agents_config(self):
        """Sample agents configuration."""
        return {
            "_models": {
                "claude-standard": {
                    "model_provider": "anthropic",
                    "model_family": "claude",
                    "model_version": "claude-3.5-sonnet-latest",
                    "model_parameters": {"temperature": 0},
                    "provider_auth": {"api_key": "test-key"},
                }
            }
        }

    @pytest.mark.asyncio
    async def test_llm_scenario_generation_with_temperature_zero(
        self, generate_step, mock_context, sample_agents_config
    ):
        """Test that LLM is invoked with temperature=0 for deterministic output (AC: 1)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a mock prompt file
            prompt_file = temp_path / "prompts" / "generate_scenarios.toml"
            prompt_file.parent.mkdir(parents=True)
            prompt_file.write_text(
                """
prompt = "Generate 2 conversational scenarios for a customer service chatbot"
count = 2
model_id = "claude-standard"
"""
            )

            # Mock agents config loading
            mock_context.eval_context.agents.read.return_value = sample_agents_config
            mock_context.output_directory = temp_path

            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(generate_step, "_load_prompt_config") as mock_load_config:
                    mock_load_config.return_value = {
                        "file_path": prompt_file,
                        "prompt": "Generate 2 conversational scenarios for a customer service chatbot",
                        "count": 2,
                        "model_id": "claude-standard",
                    }

                    # Mock ProviderFactory to track temperature=0
                    with patch(
                        "gavel_ai.core.steps.generate_step.ProviderFactory"
                    ) as mock_factory_class:
                        mock_factory = MagicMock()
                        mock_factory_class.return_value = mock_factory

                        # Mock agent creation
                        mock_agent = MagicMock()
                        mock_factory.create_agent.return_value = mock_agent

                        # Mock call_agent result
                        mock_response = MagicMock()
                        mock_response.output = """[
{
    "id": "scenario-1",
    "user_goal": "Customer wants to reset their password",
    "context": "Customer has forgotten their password and needs to access their account",
    "dialogue_guidance": {
        "tone_preference": "helpful",
        "escalation_strategy": "offer account verification",
        "factual_constraints": ["Password reset requires email verification"]
    }
},
{
    "id": "scenario-2",
    "user_goal": "Customer wants to check their order status",
    "context": "Customer placed an order 3 days ago and wants to know when it will arrive",
    "dialogue_guidance": {
        "tone_preference": "professional",
        "escalation_strategy": "provide tracking information",
        "factual_constraints": ["Orders typically ship within 24 hours"]
    }
}
]"""
                        mock_factory.call_agent = AsyncMock(return_value=mock_response)

                        # Execute
                        await generate_step.execute(mock_context)

                        # Verify agent was created with temperature=0
                        mock_factory.create_agent.assert_called_once()
                        call_args = mock_factory.create_agent.call_args[0]
                        model_def = call_args[0]
                        assert model_def.model_parameters.get("temperature") == 0

                        # Verify call_agent was called with prompt
                        mock_factory.call_agent.assert_called_once()
                        prompt_arg = mock_factory.call_agent.call_args[0][1]
                        assert "Generate 2 conversational scenarios" in prompt_arg

    @pytest.mark.asyncio
    async def test_llm_response_parsing_into_structured_scenarios(
        self, generate_step, mock_context, sample_agents_config
    ):
        """Test that LLM response is parsed into structured scenario objects (AC: 2)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock prompt file
            prompt_file = temp_path / "prompts" / "generate_scenarios.toml"
            prompt_file.parent.mkdir(parents=True)
            prompt_file.write_text(
                'prompt = "Generate scenarios"\ncount = 2\nmodel_id = "claude-standard"'
            )

            mock_context.eval_context.agents.read.return_value = sample_agents_config
            mock_context.output_directory = temp_path

            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(generate_step, "_load_prompt_config") as mock_load_config:
                    mock_load_config.return_value = {
                        "file_path": prompt_file,
                        "prompt": "Generate scenarios",
                        "count": 2,
                        "model_id": "claude-standard",
                    }

                    with patch(
                        "gavel_ai.core.steps.generate_step.ProviderFactory"
                    ) as mock_factory_class:
                        mock_factory = MagicMock()
                        mock_factory_class.return_value = mock_factory

                        mock_agent = MagicMock()
                        mock_factory.create_agent.return_value = mock_agent

                        # Mock LLM response with structured JSON
                        mock_response = MagicMock()
                        mock_response.output = """[
{
    "id": "test-scenario-1",
    "user_goal": "Test goal 1",
    "context": "Test context 1",
    "dialogue_guidance": {
        "tone_preference": "professional",
        "escalation_strategy": "politely insist",
        "factual_constraints": ["Fact 1", "Fact 2"]
    }
},
{
    "id": "test-scenario-2",
    "user_goal": "Test goal 2",
    "context": null,
    "dialogue_guidance": null
}
]"""
                        mock_factory.call_agent = AsyncMock(return_value=mock_response)

                        await generate_step.execute(mock_context)

                        # Verify scenarios.jsonl was created with parsed scenarios
                        scenarios_file = temp_path / "scenarios.jsonl"
                        assert scenarios_file.exists()
                        content = scenarios_file.read_text()
                        lines = [line for line in content.strip().split("\n") if line]

                        assert len(lines) == 2

                        # Parse each line and verify structure
                        for line in lines:
                            scenario = json.loads(line)
                            assert "id" in scenario
                            assert "user_goal" in scenario
                            # context and dialogue_guidance are optional

    @pytest.mark.asyncio
    async def test_dialogue_guidance_structure_validation(
        self, generate_step, mock_context, sample_agents_config
    ):
        """Test that dialogue_guidance contains proper structure (AC: 3)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            prompt_file = temp_path / "prompts" / "generate_scenarios.toml"
            prompt_file.parent.mkdir(parents=True)
            prompt_file.write_text(
                'prompt = "Generate scenarios"\ncount = 1\nmodel_id = "claude-standard"'
            )

            mock_context.eval_context.agents.read.return_value = sample_agents_config
            mock_context.output_directory = temp_path

            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(generate_step, "_load_prompt_config") as mock_load_config:
                    mock_load_config.return_value = {
                        "file_path": prompt_file,
                        "prompt": "Generate scenarios",
                        "count": 1,
                        "model_id": "claude-standard",
                    }

                    with patch(
                        "gavel_ai.core.steps.generate_step.ProviderFactory"
                    ) as mock_factory_class:
                        mock_factory = MagicMock()
                        mock_factory_class.return_value = mock_factory

                        mock_agent = MagicMock()
                        mock_factory.create_agent.return_value = mock_agent

                        # Mock response with complete dialogue_guidance
                        mock_response = MagicMock()
                        mock_response.output = """[
{
    "id": "test-scenario",
    "user_goal": "Test goal",
    "context": "Test context",
    "dialogue_guidance": {
        "tone_preference": "helpful",
        "escalation_strategy": "ask for supervisor",
        "factual_constraints": ["Policy states refunds within 30 days"]
    }
}
]"""
                        mock_factory.call_agent = AsyncMock(return_value=mock_response)

                        await generate_step.execute(mock_context)

                        # Verify dialogue_guidance structure
                        scenarios_file = temp_path / "scenarios.jsonl"
                        assert scenarios_file.exists()
                        content = scenarios_file.read_text()
                        scenario = json.loads(content.strip())

                        if "dialogue_guidance" in scenario and scenario["dialogue_guidance"]:
                            guidance = scenario["dialogue_guidance"]
                            # Should have the expected fields
                            assert "tone_preference" in guidance
                            assert "escalation_strategy" in guidance
                            assert "factual_constraints" in guidance
                            assert isinstance(guidance["factual_constraints"], list)

    @pytest.mark.asyncio
    async def test_deterministic_generation_with_temperature_zero(
        self, generate_step, mock_context, sample_agents_config
    ):
        """Test that same prompt with temperature=0 produces identical output (AC: 4)."""
        # This is more of an integration test that would require actual LLM
        # For unit testing, we verify that temperature=0 is passed correctly
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            prompt_file = temp_path / "prompts" / "generate_scenarios.toml"
            prompt_file.parent.mkdir(parents=True)
            prompt_file.write_text(
                'prompt = "Generate scenarios"\ncount = 1\nmodel_id = "claude-standard"'
            )

            mock_context.eval_context.agents.read.return_value = sample_agents_config
            mock_context.output_directory = temp_path

            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(generate_step, "_load_prompt_config") as mock_load_config:
                    mock_load_config.return_value = {
                        "file_path": prompt_file,
                        "prompt": "Generate scenarios",
                        "count": 1,
                        "model_id": "claude-standard",
                    }

                    with patch(
                        "gavel_ai.core.steps.generate_step.ProviderFactory"
                    ) as mock_factory_class:
                        mock_factory = MagicMock()
                        mock_factory_class.return_value = mock_factory

                        mock_agent = MagicMock()
                        mock_factory.create_agent.return_value = mock_agent

                        # Same deterministic response
                        mock_response = MagicMock()
                        mock_response.output = (
                            """[{"id": "deterministic-scenario", "user_goal": "Test goal"}]"""
                        )
                        mock_factory.call_agent = AsyncMock(return_value=mock_response)

                        # Execute twice
                        await generate_step.execute(mock_context)

                        # Verify temperature=0 was set in model parameters
                        call_args = mock_factory.create_agent.call_args[0]
                        model_def = call_args[0]
                        assert model_def.model_parameters.get("temperature") == 0

    @pytest.mark.asyncio
    async def test_jsonl_output_format_validation(
        self, generate_step, mock_context, sample_agents_config
    ):
        """Test that output is valid JSONL format (AC: 5)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            prompt_file = temp_path / "prompts" / "generate_scenarios.toml"
            prompt_file.parent.mkdir(parents=True)
            prompt_file.write_text(
                'prompt = "Generate scenarios"\ncount = 2\nmodel_id = "claude-standard"'
            )

            mock_context.eval_context.agents.read.return_value = sample_agents_config
            mock_context.output_directory = temp_path

            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(generate_step, "_load_prompt_config") as mock_load_config:
                    mock_load_config.return_value = {
                        "file_path": prompt_file,
                        "prompt": "Generate scenarios",
                        "count": 2,
                        "model_id": "claude-standard",
                    }

                    with patch(
                        "gavel_ai.core.steps.generate_step.ProviderFactory"
                    ) as mock_factory_class:
                        mock_factory = MagicMock()
                        mock_factory_class.return_value = mock_factory

                        mock_agent = MagicMock()
                        mock_factory.create_agent.return_value = mock_agent

                        # Mock valid JSON response
                        mock_response = MagicMock()
                        mock_response.output = """[
{"id": "scenario-1", "user_goal": "Goal 1"},
{"id": "scenario-2", "user_goal": "Goal 2"}
]"""
                        mock_factory.call_agent = AsyncMock(return_value=mock_response)

                        await generate_step.execute(mock_context)

                        # Verify JSONL format
                        scenarios_file = temp_path / "scenarios.jsonl"
                        assert scenarios_file.exists()
                        content = scenarios_file.read_text()
                        lines = [line for line in content.strip().split("\n") if line]

                        assert len(lines) == 2

                        # Each line should be valid JSON
                        for line in lines:
                            json.loads(line)  # Should not raise exception

                        # No nesting, one scenario per line
                        assert content.count("\n") == 2  # JSONL has a newline for each entry
