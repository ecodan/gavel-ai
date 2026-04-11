import pytest

pytestmark = pytest.mark.unit
"""
Test module for processor base classes and interfaces (Story 3.1 - Task 2).

Tests for InputProcessor ABC contract and interface requirements.
"""

from abc import ABC

import pytest


class TestInputProcessorABC:
    """Test InputProcessor abstract base class contract."""

    def test_input_processor_cannot_be_instantiated(self):
        """InputProcessor ABC cannot be instantiated directly."""
        from gavel_ai.core.models import ProcessorConfig
        from gavel_ai.processors.base import InputProcessor

        with pytest.raises(TypeError) as exc_info:
            InputProcessor(ProcessorConfig(processor_type="test"))

        assert "abstract" in str(exc_info.value).lower()

    def test_input_processor_is_abc(self):
        """InputProcessor is an ABC (Abstract Base Class)."""
        from gavel_ai.processors.base import InputProcessor

        assert issubclass(InputProcessor, ABC)

    def test_input_processor_has_init_method(self):
        """InputProcessor has __init__(config: ProcessorConfig) constructor."""
        from gavel_ai.processors.base import InputProcessor

        # Check __init__ signature exists
        assert hasattr(InputProcessor, "__init__")

    def test_input_processor_has_process_method(self):
        """InputProcessor has async process method."""
        from gavel_ai.processors.base import InputProcessor

        assert hasattr(InputProcessor, "process")
        # Verify it's marked as abstract
        assert hasattr(InputProcessor.process, "__isabstractmethod__")

    def test_input_processor_has_tracer_attribute(self):
        """InputProcessor instances have tracer attribute from get_tracer."""
        from gavel_ai.core.models import ProcessorConfig
        from gavel_ai.processors.base import InputProcessor

        # Create a concrete implementation for testing
        class ConcreteProcessor(InputProcessor):
            async def process(self, inputs):
                return {"output": "test"}

        processor = ConcreteProcessor(ProcessorConfig(processor_type="test"))
        assert hasattr(processor, "tracer")
        assert processor.tracer is not None


class TestConcreteProcessorContract:
    """Test that concrete processors must implement all abstract methods."""

    def test_concrete_processor_must_implement_process(self):
        """Concrete processor must implement process method."""
        from gavel_ai.core.models import ProcessorConfig
        from gavel_ai.processors.base import InputProcessor

        # Missing process implementation
        class IncompleteProcessor(InputProcessor):
            pass

        with pytest.raises(TypeError) as exc_info:
            IncompleteProcessor(ProcessorConfig(processor_type="test"))

        assert "process" in str(exc_info.value).lower()

    def test_concrete_processor_can_be_instantiated_when_complete(self):
        """Concrete processor with process() implemented can be instantiated."""
        from gavel_ai.core.models import ProcessorConfig
        from gavel_ai.processors.base import InputProcessor

        class CompleteProcessor(InputProcessor):
            async def process(self, inputs):
                return {"output": "test"}

        processor = CompleteProcessor(ProcessorConfig(processor_type="test"))
        assert processor is not None
        assert processor.config.processor_type == "test"

    def test_concrete_processor_process_is_async(self):
        """Concrete processor process method is async."""
        import inspect

        from gavel_ai.core.models import ProcessorConfig
        from gavel_ai.processors.base import InputProcessor

        class CompleteProcessor(InputProcessor):
            async def process(self, inputs):
                return {"output": "test"}

        processor = CompleteProcessor(ProcessorConfig(processor_type="test"))
        assert inspect.iscoroutinefunction(processor.process)


class TestProcessorConfigIntegration:
    """Test that ProcessorConfig validation works with InputProcessor."""

    def test_processor_receives_config_in_constructor(self):
        """Processor stores config passed to constructor."""
        from gavel_ai.core.models import ProcessorConfig
        from gavel_ai.processors.base import InputProcessor

        class TestProcessor(InputProcessor):
            async def process(self, inputs):
                return {"output": "test"}

        config = ProcessorConfig(processor_type="my_processor")
        processor = TestProcessor(config)
        assert processor.config.processor_type == "my_processor"

    def test_processor_config_ignores_unknown_fields(self):
        """ProcessorConfig extra='ignore' works when passed to processor."""
        from gavel_ai.core.models import ProcessorConfig
        from gavel_ai.processors.base import InputProcessor

        class TestProcessor(InputProcessor):
            async def process(self, inputs):
                return {"output": "test"}

        config_data = {"processor_type": "test", "unknown_field": "ignored"}
        config = ProcessorConfig(**config_data)
        processor = TestProcessor(config)
        assert processor.config.processor_type == "test"

    @pytest.mark.asyncio
    async def test_processor_async_process_call(self):
        """Test that async process() method can actually be called."""
        from gavel_ai.core.models import Input, ProcessorConfig, ProcessorResult
        from gavel_ai.processors.base import InputProcessor

        class TestProcessor(InputProcessor):
            async def process(self, inputs):
                return ProcessorResult(output=f"Processed {len(inputs)} inputs")

        processor = TestProcessor(ProcessorConfig(processor_type="test"))
        input_data = [Input(id="1", text="test data")]

        # Call the async method
        result = await processor.process(input_data)

        assert isinstance(result, ProcessorResult)
        assert "Processed 1 inputs" in result.output
