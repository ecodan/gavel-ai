"""
Tests for GenerateStep implementation.

Tests the scenario generation functionality that creates conversational
scenarios from prompts using LLM generation.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gavel_ai.core.contexts import RunContext
from gavel_ai.core.exceptions import ProcessorError
from gavel_ai.core.steps.generate_step import GenerateStep


class TestGenerateStep:
    """Test GenerateStep implementation."""

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

    def test_generatestep_inherits_from_step(self, generate_step):
        """Test that GenerateStep implements the Step interface."""
        from gavel_ai.core.steps.base import Step

        assert isinstance(generate_step, Step)
        assert hasattr(generate_step, "phase")
        assert hasattr(generate_step, "execute")
        assert callable(generate_step.execute)

    def test_phase_property(self, generate_step):
        """Test that phase returns the correct StepPhase."""
        from gavel_ai.core.steps.base import StepPhase

        assert generate_step.phase == StepPhase.SCENARIO_PROCESSING

    @pytest.mark.asyncio
    async def test_execute_method_signature(self, generate_step, mock_context):
        """Test that execute method has correct signature."""
        with patch.object(generate_step, "_load_prompt_config") as mock_load:
            mock_load.return_value = {
                "prompt": "test",
                "count": 1,
                "model_id": "claude-standard",
                "file_path": Path("test.toml"),
            }
            with patch.object(generate_step, "_generate_scenarios", return_value=[]):
                with patch.object(
                    generate_step, "_save_scenarios", return_value=Path("test.jsonl")
                ):
                    await generate_step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_missing_prompt_file(self, generate_step, mock_context):
        """Test that execute raises ProcessorError when prompt file is missing."""
        # This tests error handling requirement
        # Mock the prompt file to not exist
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(ProcessorError):
                await generate_step.execute(mock_context)

    @pytest.mark.asyncio
    async def test_execute_outputs_scenarios_jsonl(self, generate_step, mock_context):
        """Test that execute outputs scenarios in JSONL format."""
        # This tests AC3: output is scenarios.jsonl with generated scenarios
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            scenarios_file = temp_path / "scenarios.jsonl"

            # Create a mock prompt file
            prompt_file = temp_path / "prompts" / "generate_scenarios.toml"
            prompt_file.parent.mkdir(parents=True)
            prompt_file.write_text('prompt = "Generate test scenarios"\ncount = 5')

            # Mock context to point to temp directory
            mock_context.output_directory = temp_path

            # Mock Path to point to our test prompt file
            with patch("pathlib.Path.exists", return_value=True):
                with patch.object(generate_step, "_load_prompt_config") as mock_load:
                    mock_load.return_value = {
                        "prompt": "Generate test scenarios",
                        "count": 5,
                        "model_id": "claude-standard",
                        "file_path": prompt_file,
                    }

                    # Mock agents config for _generate_scenarios
                    mock_context.eval_context.agents.read.return_value = {
                        "_models": {
                            "claude-standard": {
                                "model_provider": "anthropic",
                                "model_family": "claude",
                                "model_version": "claude-3-sonnet",
                                "provider_auth": {"api_key": "test"},
                                "model_parameters": {"temperature": 0},
                            }
                        }
                    }

                    # Mock ProviderFactory to avoid real calls
                    with patch(
                        "gavel_ai.core.steps.generate_step.ProviderFactory"
                    ) as mock_factory_class:
                        mock_factory = MagicMock()
                        mock_factory_class.return_value = mock_factory
                        mock_factory.call_agent = AsyncMock(
                            return_value=MagicMock(output='[{"id": "1", "user_goal": "test"}]')
                        )

                        await generate_step.execute(mock_context)

                    # Once implemented, this should create scenarios.jsonl
                    assert scenarios_file.exists()

                    # Verify content is JSONL format
                    content = scenarios_file.read_text()
                    lines = [line for line in content.strip().split("\n") if line]
                    assert len(lines) > 0

                    # Each line should be valid JSON
                    for line in lines:
                        json.loads(line)

    @pytest.mark.asyncio
    async def test_generated_scenario_format(self, generate_step, mock_context):
        """Test that generated scenarios have required fields."""
        # This tests AC4: each scenario contains id, user_goal (required),
        # context (optional), dialogue_guidance (optional)

        # Mock scenario generation to return known data
        mock_scenarios = [
            {
                "id": "test-scenario-1",
                "user_goal": "Test user goal",
                "context": "Test context",
                "dialogue_guidance": {"tone_preference": "professional"},
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            scenarios_file = temp_path / "scenarios.jsonl"

            # Create a mock prompt file
            prompt_file = temp_path / "prompts" / "generate_scenarios.toml"
            prompt_file.parent.mkdir(parents=True)
            prompt_file.write_text('prompt = "Generate test scenarios"\ncount = 1')

            # Mock context to point to temp directory
            mock_context.output_directory = temp_path

            # Mock the prompt loading and scenario generation
            with patch.object(generate_step, "_load_prompt_config") as mock_load:
                mock_load.return_value = {
                    "file_path": prompt_file,
                    "prompt": "Generate test scenarios",
                    "count": 1,
                    "model_id": "claude-standard",
                }

                with patch.object(
                    generate_step, "_generate_scenarios", return_value=mock_scenarios
                ):
                    await generate_step.execute(mock_context)

                    # Once implemented, should validate scenario format
                    assert scenarios_file.exists()
                    content = scenarios_file.read_text()
                    lines = [line for line in content.strip().split("\n") if line]

                    for line in lines:
                        scenario_data = json.loads(line)
                        assert "id" in scenario_data
                        assert "user_goal" in scenario_data
                        # context and dialogue_guidance are optional

    @pytest.mark.asyncio
    async def test_telemetry_recording(self, generate_step, mock_context):
        """Test that execute records telemetry with required attributes."""
        # This tests AC5: span recorded with trace_id, scenario_count,
        # prompt_file used, LLM model

        with patch("gavel_ai.core.steps.base.get_tracer") as mock_get_tracer:
            mock_tracer_instance = MagicMock()
            mock_span = MagicMock()
            mock_get_tracer.return_value = mock_tracer_instance

            # Ensure the span mock is correctly set up for context manager
            mock_tracer_instance.start_as_current_span.return_value.__enter__.return_value = (
                mock_span
            )
            mock_tracer_instance.start_as_current_span.return_value.__exit__.return_value = None

            step = GenerateStep(MagicMock())

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                # Create a mock prompt file
                prompt_file = temp_path / "prompts" / "generate_scenarios.toml"
                prompt_file.parent.mkdir(parents=True)
                prompt_file.write_text('prompt = "Generate test scenarios"\ncount = 1')

                # Mock context and prompt loading
                mock_context.output_directory = temp_path
                mock_context.eval_context.eval_config.read.return_value = {}

                with patch.object(step, "_load_prompt_config") as mock_load_config:
                    mock_load_config.return_value = {
                        "file_path": prompt_file,
                        "prompt": "Generate test scenarios",
                        "count": 1,
                        "model_id": "claude-standard",
                    }

                    with patch.object(
                        step, "_generate_scenarios", return_value=[{"id": "1", "user_goal": "test"}]
                    ):
                        with patch.object(
                            step,
                            "_save_scenarios",
                            return_value=Path(temp_path) / "scenarios.jsonl",
                        ):
                            await step.execute(mock_context)

                            # Check that set_attribute was called
                            assert mock_span.set_attribute.called

                            # Verify critical attributes were set
                            calls = [
                                args[0] for args, kwargs in mock_span.set_attribute.call_args_list
                            ]
                            assert "generate.model_id" in calls
                            assert "generate.scenario_count" in calls
                            assert "generate.prompt_file" in calls
