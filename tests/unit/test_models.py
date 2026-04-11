import pytest

pytestmark = pytest.mark.unit
"""
Test module for core data models (Story 3.1 - Task 1).

Tests for Input, ProcessorConfig, and ProcessorResult Pydantic models.
"""

import pytest
from pydantic import ValidationError


class TestInputModel:
    """Test Input Pydantic model."""

    def test_input_model_basic_creation(self):
        """Input model can be created with required fields."""
        from gavel_ai.core.models import Input

        input_data = Input(id="test-1", text="Hello, world!")
        assert input_data.id == "test-1"
        assert input_data.text == "Hello, world!"
        assert input_data.metadata == {}

    def test_input_model_with_metadata(self):
        """Input model accepts metadata dict."""
        from gavel_ai.core.models import Input

        input_data = Input(id="test-2", text="Test input", metadata={"key": "value", "count": 42})
        assert input_data.metadata["key"] == "value"
        assert input_data.metadata["count"] == 42

    def test_input_model_requires_id(self):
        """Input model requires id field."""
        from gavel_ai.core.models import Input

        with pytest.raises(ValidationError) as exc_info:
            Input(text="No ID provided")

        assert "id" in str(exc_info.value)

    def test_input_model_requires_text(self):
        """Input model requires text field."""
        from gavel_ai.core.models import Input

        with pytest.raises(ValidationError) as exc_info:
            Input(id="test-3")

        assert "text" in str(exc_info.value)

    def test_input_model_uses_snake_case_fields(self):
        """Input model uses snake_case field names."""
        from gavel_ai.core.models import Input

        input_data = Input(id="test", text="data")
        # Verify snake_case field access works
        assert hasattr(input_data, "id")
        assert hasattr(input_data, "text")
        assert hasattr(input_data, "metadata")


class TestProcessorConfigModel:
    """Test ProcessorConfig Pydantic model."""

    def test_processor_config_basic_creation(self):
        """ProcessorConfig can be created with minimal fields."""
        from gavel_ai.core.models import ProcessorConfig

        config = ProcessorConfig(processor_type="test_processor")
        assert config.processor_type == "test_processor"

    def test_processor_config_extra_ignore(self):
        """ProcessorConfig ignores unknown fields for forward compatibility."""
        from gavel_ai.core.models import ProcessorConfig

        config_data = {
            "processor_type": "test",
            "unknown_future_field": "value",
            "another_unknown": 123,
        }
        config = ProcessorConfig(**config_data)
        assert config.processor_type == "test"
        # Unknown fields should be ignored (not raise error)
        assert not hasattr(config, "unknown_future_field")

    def test_processor_config_requires_processor_type(self):
        """ProcessorConfig requires processor_type field."""
        from gavel_ai.core.models import ProcessorConfig

        with pytest.raises(ValidationError) as exc_info:
            ProcessorConfig()

        assert "processor_type" in str(exc_info.value)

    def test_processor_config_uses_snake_case_fields(self):
        """ProcessorConfig uses snake_case field names."""
        from gavel_ai.core.models import ProcessorConfig

        config = ProcessorConfig(processor_type="test")
        assert hasattr(config, "processor_type")

    def test_processor_config_behavioral_rules(self):
        """ProcessorConfig includes behavioral rule fields."""
        from gavel_ai.core.models import ProcessorConfig

        config = ProcessorConfig(
            processor_type="test",
            parallelism=4,
            timeout_seconds=60,
            error_handling="continue_on_error",
        )
        assert config.parallelism == 4
        assert config.timeout_seconds == 60
        assert config.error_handling == "continue_on_error"

    def test_processor_config_default_behavioral_rules(self):
        """ProcessorConfig has sensible defaults for behavioral rules."""
        from gavel_ai.core.models import ProcessorConfig

        config = ProcessorConfig(processor_type="test")
        assert config.parallelism == 1
        assert config.timeout_seconds == 30
        assert config.error_handling == "fail_fast"


class TestProcessorResultModel:
    """Test ProcessorResult Pydantic model."""

    def test_processor_result_basic_creation(self):
        """ProcessorResult can be created with minimal fields."""
        from gavel_ai.core.models import ProcessorResult

        result = ProcessorResult(output="test output")
        assert result.output == "test output"
        assert result.metadata == {}
        assert result.error is None

    def test_processor_result_with_metadata(self):
        """ProcessorResult accepts metadata dict."""
        from gavel_ai.core.models import ProcessorResult

        result = ProcessorResult(
            output="result",
            metadata={"duration_ms": 150, "tokens_used": 100},
        )
        assert result.metadata["duration_ms"] == 150
        assert result.metadata["tokens_used"] == 100

    def test_processor_result_with_error(self):
        """ProcessorResult accepts optional error field."""
        from gavel_ai.core.models import ProcessorResult

        result = ProcessorResult(output="", error="Processing failed - timeout occurred")
        assert result.error == "Processing failed - timeout occurred"
        assert result.output == ""

    def test_processor_result_requires_output(self):
        """ProcessorResult requires output field."""
        from gavel_ai.core.models import ProcessorResult

        with pytest.raises(ValidationError) as exc_info:
            ProcessorResult()

        assert "output" in str(exc_info.value)

    def test_processor_result_uses_snake_case_fields(self):
        """ProcessorResult uses snake_case field names."""
        from gavel_ai.core.models import ProcessorResult

        result = ProcessorResult(output="test")
        assert hasattr(result, "output")
        assert hasattr(result, "metadata")
        assert hasattr(result, "error")

    def test_processor_result_with_dict_output(self):
        """ProcessorResult accepts dict output (not just string)."""
        from gavel_ai.core.models import ProcessorResult

        output_data = {"tokens_used": 150, "cost": 0.05}
        result = ProcessorResult(output=output_data)
        assert result.output == output_data
        assert isinstance(result.output, dict)

    def test_processor_result_with_list_output(self):
        """ProcessorResult accepts list output."""
        from gavel_ai.core.models import ProcessorResult

        output_data = [1, 2, 3, "result"]
        result = ProcessorResult(output=output_data)
        assert result.output == output_data
        assert isinstance(result.output, list)
