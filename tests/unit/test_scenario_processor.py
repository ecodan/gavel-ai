"""
Unit tests for ScenarioProcessor.

Tests multi-turn conversation handling and context accumulation.
"""

import pytest
from unittest.mock import AsyncMock

from gavel_ai.core.models import Input, ProcessorConfig, ProcessorResult
from gavel_ai.processors.base import InputProcessor
from gavel_ai.processors.scenario_processor import ScenarioProcessor


class MockInnerProcessor(InputProcessor):
    """Mock inner processor for testing."""

    async def process(self, inputs):
        """Mock process that echoes input."""
        return ProcessorResult(
            output=f"Response to: {inputs[0].text}",
            metadata={"tokens": {"total": 100}, "latency_ms": 50},
        )


class TestScenarioProcessorInitialization:
    """Test ScenarioProcessor initialization."""

    def test_init_with_inner_processor(self):
        """ScenarioProcessor initializes with inner processor."""
        config = ProcessorConfig(processor_type="scenario")
        inner = MockInnerProcessor(ProcessorConfig(processor_type="prompt_input"))
        processor = ScenarioProcessor(config, inner)

        assert processor.inner_processor == inner
        assert processor.config == config

    def test_init_inherits_from_input_processor(self):
        """ScenarioProcessor inherits from InputProcessor."""
        config = ProcessorConfig(processor_type="scenario")
        inner = MockInnerProcessor(ProcessorConfig(processor_type="prompt_input"))
        processor = ScenarioProcessor(config, inner)

        assert isinstance(processor, InputProcessor)


class TestMultiTurnProcessing:
    """Test multi-turn conversation processing."""

    @pytest.mark.asyncio
    async def test_process_single_turn(self):
        """Process single turn returns formatted output."""
        config = ProcessorConfig(processor_type="scenario")
        inner = MockInnerProcessor(ProcessorConfig(processor_type="prompt_input"))
        processor = ScenarioProcessor(config, inner)

        inputs = [Input(id="1", text="Hello", metadata={})]
        result = await processor.process(inputs)

        assert isinstance(result, ProcessorResult)
        assert "Turn 1:" in result.output
        assert "Response to: Hello" in result.output

    @pytest.mark.asyncio
    async def test_process_multiple_turns(self):
        """Process multiple turns accumulates conversation history."""
        config = ProcessorConfig(processor_type="scenario")
        inner = MockInnerProcessor(ProcessorConfig(processor_type="prompt_input"))
        processor = ScenarioProcessor(config, inner)

        inputs = [
            Input(id="1", text="Hello", metadata={}),
            Input(id="2", text="How are you?", metadata={}),
            Input(id="3", text="Goodbye", metadata={}),
        ]
        result = await processor.process(inputs)

        # Check all turns in output
        assert "Turn 1:" in result.output
        assert "Turn 2:" in result.output
        assert "Turn 3:" in result.output

    @pytest.mark.asyncio
    async def test_conversation_history_accumulated(self):
        """Conversation history is added to subsequent turns."""
        config = ProcessorConfig(processor_type="scenario")
        inner = MockInnerProcessor(ProcessorConfig(processor_type="prompt_input"))

        # Track metadata passed to inner processor
        calls = []

        async def track_calls(inputs):
            calls.append(inputs[0].metadata.copy())
            return ProcessorResult(output=f"Turn {len(calls)}", metadata={})

        inner.process = AsyncMock(side_effect=track_calls)

        processor = ScenarioProcessor(config, inner)

        inputs = [
            Input(id="1", text="First", metadata={}),
            Input(id="2", text="Second", metadata={}),
        ]
        await processor.process(inputs)

        # First turn has no history
        assert "conversation_history" not in calls[0]

        # Second turn has history (note: metadata is mutated, so both turns appear)
        assert "conversation_history" in calls[1]
        assert len(calls[1]["conversation_history"]) >= 1
        assert calls[1]["conversation_history"][0]["turn"] == 1


class TestMetadataAggregation:
    """Test metadata aggregation across turns."""

    @pytest.mark.asyncio
    async def test_metadata_aggregates_totals(self):
        """Metadata with total_* keys are summed."""
        config = ProcessorConfig(processor_type="scenario")
        inner = MockInnerProcessor(ProcessorConfig(processor_type="prompt_input"))

        # Mock inner processor to return metadata
        async def mock_with_metadata(inputs):
            return ProcessorResult(
                output="Response",
                metadata={"total_tokens": 100, "total_latency_ms": 50},
            )

        inner.process = AsyncMock(side_effect=mock_with_metadata)

        processor = ScenarioProcessor(config, inner)

        inputs = [
            Input(id="1", text="First", metadata={}),
            Input(id="2", text="Second", metadata={}),
        ]
        result = await processor.process(inputs)

        # Totals should be summed
        assert result.metadata["total_tokens"] == 200
        assert result.metadata["total_latency_ms"] == 100

    @pytest.mark.asyncio
    async def test_metadata_preserves_per_turn(self):
        """Non-total metadata is preserved per turn."""
        config = ProcessorConfig(processor_type="scenario")
        inner = MockInnerProcessor(ProcessorConfig(processor_type="prompt_input"))

        # Mock inner processor with unique metadata per turn
        turn_count = [0]

        async def mock_with_unique_metadata(inputs):
            turn_count[0] += 1
            return ProcessorResult(
                output="Response",
                metadata={"model": f"model-v{turn_count[0]}", "status": "ok"},
            )

        inner.process = AsyncMock(side_effect=mock_with_unique_metadata)

        processor = ScenarioProcessor(config, inner)

        inputs = [
            Input(id="1", text="First", metadata={}),
            Input(id="2", text="Second", metadata={}),
        ]
        result = await processor.process(inputs)

        # Per-turn metadata should be preserved with turn prefix
        assert result.metadata["turn_1_model"] == "model-v1"
        assert result.metadata["turn_2_model"] == "model-v2"

    @pytest.mark.asyncio
    async def test_turns_count_in_metadata(self):
        """Metadata includes turn count."""
        config = ProcessorConfig(processor_type="scenario")
        inner = MockInnerProcessor(ProcessorConfig(processor_type="prompt_input"))
        processor = ScenarioProcessor(config, inner)

        inputs = [
            Input(id="1", text="First", metadata={}),
            Input(id="2", text="Second", metadata={}),
            Input(id="3", text="Third", metadata={}),
        ]
        result = await processor.process(inputs)

        assert result.metadata["turns"] == 3
