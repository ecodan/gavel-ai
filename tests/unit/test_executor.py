"""
Unit tests for Executor.

Tests concurrent execution, batching, and error handling modes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from gavel_ai.core.executor import Executor
from gavel_ai.core.models import Input, ProcessorConfig, ProcessorResult
from gavel_ai.processors.base import InputProcessor


class MockProcessor(InputProcessor):
    """Mock processor for testing."""

    async def process(self, inputs):
        """Mock process implementation."""
        return ProcessorResult(
            output=f"Processed {len(inputs)} inputs",
            metadata={"count": len(inputs)},
        )


class TestExecutorInitialization:
    """Test Executor initialization."""

    def test_init_with_defaults(self):
        """Executor initializes with default values."""
        config = ProcessorConfig(processor_type="test")
        processor = MockProcessor(config)
        executor = Executor(processor)

        assert executor.processor == processor
        assert executor.parallelism == 4
        assert executor.error_handling == "collect_all"

    def test_init_with_custom_parallelism(self):
        """Executor accepts custom parallelism."""
        config = ProcessorConfig(processor_type="test")
        processor = MockProcessor(config)
        executor = Executor(processor, parallelism=8)

        assert executor.parallelism == 8

    def test_init_with_fail_fast_mode(self):
        """Executor accepts fail_fast error handling."""
        config = ProcessorConfig(processor_type="test")
        processor = MockProcessor(config)
        executor = Executor(processor, error_handling="fail_fast")

        assert executor.error_handling == "fail_fast"


class TestExecutorExecution:
    """Test Executor execution behavior."""

    @pytest.mark.asyncio
    async def test_execute_single_input(self):
        """Execute with single input returns one result."""
        config = ProcessorConfig(processor_type="test")
        processor = MockProcessor(config)
        executor = Executor(processor)

        inputs = [Input(id="1", text="test", metadata={})]
        results = await executor.execute(inputs)

        assert len(results) == 1
        assert isinstance(results[0], ProcessorResult)

    @pytest.mark.asyncio
    async def test_execute_multiple_inputs(self):
        """Execute with multiple inputs returns all results."""
        config = ProcessorConfig(processor_type="test")
        processor = MockProcessor(config)
        executor = Executor(processor)

        inputs = [
            Input(id="1", text="test1", metadata={}),
            Input(id="2", text="test2", metadata={}),
            Input(id="3", text="test3", metadata={}),
        ]
        results = await executor.execute(inputs)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_execute_respects_parallelism(self):
        """Execute batches inputs according to parallelism setting."""
        config = ProcessorConfig(processor_type="test")
        processor = MockProcessor(config)
        processor.process = AsyncMock(return_value=ProcessorResult(output="test", metadata={}))

        executor = Executor(processor, parallelism=2)

        inputs = [
            Input(id="1", text="test1", metadata={}),
            Input(id="2", text="test2", metadata={}),
            Input(id="3", text="test3", metadata={}),
        ]
        results = await executor.execute(inputs)

        # Should call process 3 times (one per input)
        assert processor.process.call_count == 3
        assert len(results) == 3


class TestExecutorErrorHandling:
    """Test Executor error handling modes."""

    @pytest.mark.asyncio
    async def test_collect_all_mode_captures_errors(self):
        """collect_all mode wraps errors in ProcessorResult."""
        config = ProcessorConfig(processor_type="test")
        processor = MockProcessor(config)

        # Make processor fail for specific input
        async def mock_process(inputs):
            if inputs[0].id == "2":
                raise ValueError("Test error")
            return ProcessorResult(output="success", metadata={})

        processor.process = AsyncMock(side_effect=mock_process)

        executor = Executor(processor, error_handling="collect_all")

        inputs = [
            Input(id="1", text="test1", metadata={}),
            Input(id="2", text="test2", metadata={}),
            Input(id="3", text="test3", metadata={}),
        ]
        results = await executor.execute(inputs)

        # All 3 results should be returned
        assert len(results) == 3

        # Check second result has error
        assert results[1].error is not None
        assert "Test error" in results[1].error

    @pytest.mark.asyncio
    async def test_fail_fast_mode_raises_immediately(self):
        """fail_fast mode raises on first error."""
        config = ProcessorConfig(processor_type="test")
        processor = MockProcessor(config)

        # Make processor fail
        processor.process = AsyncMock(side_effect=ValueError("Test error"))

        executor = Executor(processor, error_handling="fail_fast")

        inputs = [Input(id="1", text="test1", metadata={})]

        with pytest.raises(ValueError, match="Test error"):
            await executor.execute(inputs)
