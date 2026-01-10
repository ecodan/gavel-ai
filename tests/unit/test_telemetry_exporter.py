"""
Unit tests for TelemetryFileExporter.

Per Story 7.1: Tests for telemetry span export functionality.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExportResult
from opentelemetry.trace import SpanKind, StatusCode, TraceFlags

from gavel_ai.telemetry import TelemetryFileExporter


class MockSpanContext:
    """Mock SpanContext for testing."""

    def __init__(
        self,
        trace_id: int = 0x7E5119529BA632D81AC0DAC7B14E6A1E,
        span_id: int = 0xB636602EF135A53C,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.trace_flags = TraceFlags(1)
        self.trace_state = None
        self.is_remote = False
        self.is_valid = True


class MockParentSpanContext:
    """Mock parent span context."""

    def __init__(self, span_id: int = 0xD4ABB4363B352E2C):
        self.span_id = span_id


def create_mock_span(
    name: str = "test.span",
    trace_id: int = 0x7E5119529BA632D81AC0DAC7B14E6A1E,
    span_id: int = 0xB636602EF135A53C,
    parent_span_id: int | None = 0xD4ABB4363B352E2C,
    start_time: int = 1735674974296088000,
    end_time: int = 1735674976629510000,
    status_code: StatusCode = StatusCode.OK,
    attributes: dict | None = None,
) -> MagicMock:
    """
    Create a mock ReadableSpan for testing.

    Args:
        name: Span name
        trace_id: Trace ID as int
        span_id: Span ID as int
        parent_span_id: Parent span ID (None for root span)
        start_time: Start time in nanoseconds
        end_time: End time in nanoseconds
        status_code: Status code
        attributes: Span attributes dict

    Returns:
        Mock ReadableSpan
    """
    span = MagicMock(spec=ReadableSpan)
    span.name = name
    span.context = MockSpanContext(trace_id=trace_id, span_id=span_id)
    span.start_time = start_time
    span.end_time = end_time
    span.kind = SpanKind.INTERNAL

    # Mock status
    status = MagicMock()
    status.status_code = status_code
    span.status = status

    # Mock parent
    if parent_span_id is not None:
        span.parent = MockParentSpanContext(span_id=parent_span_id)
    else:
        span.parent = None

    # Mock attributes
    span.attributes = attributes or {}

    return span


class TestTelemetryFileExporter:
    """Tests for TelemetryFileExporter class."""

    def test_exporter_creates_file(self, tmp_path: Path) -> None:
        """TelemetryFileExporter creates telemetry.jsonl file."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        # Create mock span
        span = create_mock_span(name="test.span")

        # Export
        result = exporter.export([span])

        assert result == SpanExportResult.SUCCESS
        assert file_path.exists()

    def test_exporter_creates_directory_structure(self, tmp_path: Path) -> None:
        """TelemetryFileExporter creates parent directories if needed."""
        file_path = tmp_path / "evaluations" / "test" / "runs" / "run-123" / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        # Create mock span
        span = create_mock_span()

        # Export
        result = exporter.export([span])

        assert result == SpanExportResult.SUCCESS
        assert file_path.exists()
        assert file_path.parent.name == "run-123"

    def test_span_serialization_format(self, tmp_path: Path) -> None:
        """Spans are serialized with correct schema."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        # Create span with known values
        span = create_mock_span(
            name="llm.call",
            trace_id=0x7E5119529BA632D81AC0DAC7B14E6A1E,
            span_id=0xB636602EF135A53C,
            parent_span_id=0xD4ABB4363B352E2C,
            start_time=1735674974296088000,
            end_time=1735674976629510000,
            attributes={
                "llm.provider": "anthropic",
                "llm.model": "claude-3-5-sonnet",
            },
        )

        # Export
        result = exporter.export([span])
        assert result == SpanExportResult.SUCCESS

        # Parse and verify
        content = file_path.read_text()
        span_dict = json.loads(content.strip())

        # Verify all required fields
        assert span_dict["name"] == "llm.call"
        assert span_dict["trace_id"] == "7e5119529ba632d81ac0dac7b14e6a1e"
        assert span_dict["span_id"] == "b636602ef135a53c"
        assert span_dict["parent_id"] == "d4abb4363b352e2c"
        assert span_dict["start_time"] == 1735674974296088000
        assert span_dict["end_time"] == 1735674976629510000
        assert span_dict["duration_ns"] == 2333422000
        assert span_dict["status"] == "OK"
        assert span_dict["attributes"]["llm.provider"] == "anthropic"
        assert span_dict["attributes"]["llm.model"] == "claude-3-5-sonnet"

    def test_root_span_has_null_parent(self, tmp_path: Path) -> None:
        """Root spans have null parent_id."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        # Create root span (no parent)
        span = create_mock_span(name="root.span", parent_span_id=None)

        # Export
        result = exporter.export([span])
        assert result == SpanExportResult.SUCCESS

        # Verify parent_id is null
        content = file_path.read_text()
        span_dict = json.loads(content.strip())
        assert span_dict["parent_id"] is None

    def test_error_status_span(self, tmp_path: Path) -> None:
        """Error spans have ERROR status."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        span = create_mock_span(name="error.span", status_code=StatusCode.ERROR)

        result = exporter.export([span])
        assert result == SpanExportResult.SUCCESS

        content = file_path.read_text()
        span_dict = json.loads(content.strip())
        assert span_dict["status"] == "ERROR"

    def test_multiple_spans_appended(self, tmp_path: Path) -> None:
        """Multiple spans are appended to the same file."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        # Export first span
        span1 = create_mock_span(name="span.1")
        exporter.export([span1])

        # Export second span
        span2 = create_mock_span(name="span.2")
        exporter.export([span2])

        # Verify both spans in file
        lines = file_path.read_text().strip().split("\n")
        assert len(lines) == 2

        span1_dict = json.loads(lines[0])
        span2_dict = json.loads(lines[1])
        assert span1_dict["name"] == "span.1"
        assert span2_dict["name"] == "span.2"

    def test_batch_export(self, tmp_path: Path) -> None:
        """Multiple spans exported in single batch."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        # Create batch of spans
        spans = [
            create_mock_span(name="batch.span.1"),
            create_mock_span(name="batch.span.2"),
            create_mock_span(name="batch.span.3"),
        ]

        # Export batch
        result = exporter.export(spans)
        assert result == SpanExportResult.SUCCESS

        # Verify all spans in file
        lines = file_path.read_text().strip().split("\n")
        assert len(lines) == 3

    def test_attribute_type_handling(self, tmp_path: Path) -> None:
        """Various attribute types are handled correctly."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        span = create_mock_span(
            attributes={
                "string_attr": "value",
                "int_attr": 42,
                "float_attr": 3.14,
                "bool_attr": True,
            }
        )

        result = exporter.export([span])
        assert result == SpanExportResult.SUCCESS

        content = file_path.read_text()
        span_dict = json.loads(content.strip())
        assert span_dict["attributes"]["string_attr"] == "value"
        assert span_dict["attributes"]["int_attr"] == 42
        assert span_dict["attributes"]["float_attr"] == 3.14
        assert span_dict["attributes"]["bool_attr"] is True

    def test_tuple_attribute_converted_to_list(self, tmp_path: Path) -> None:
        """Tuple attributes are converted to lists for JSON serialization."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        span = create_mock_span(attributes={"tuple_attr": ("a", "b", "c")})

        result = exporter.export([span])
        assert result == SpanExportResult.SUCCESS

        content = file_path.read_text()
        span_dict = json.loads(content.strip())
        assert span_dict["attributes"]["tuple_attr"] == ["a", "b", "c"]

    def test_shutdown_is_noop(self, tmp_path: Path) -> None:
        """Shutdown method doesn't raise."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        # Should not raise
        exporter.shutdown()

    def test_force_flush_returns_true(self, tmp_path: Path) -> None:
        """Force flush returns True (immediate writes)."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        assert exporter.force_flush() is True

    def test_invalid_path_returns_failure(self, tmp_path: Path) -> None:
        """Invalid path returns FAILURE result."""
        # Use a path that can't be written to
        file_path = Path("/nonexistent/directory/cannot/create/telemetry.jsonl")
        exporter = TelemetryFileExporter.__new__(TelemetryFileExporter)
        exporter.file_path = file_path

        span = create_mock_span()
        result = exporter.export([span])

        assert result == SpanExportResult.FAILURE

    def test_empty_attributes_handled(self, tmp_path: Path) -> None:
        """Spans with empty/None attributes are handled."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        span = create_mock_span(attributes=None)
        span.attributes = None  # Override to test None case

        result = exporter.export([span])
        assert result == SpanExportResult.SUCCESS

        content = file_path.read_text()
        span_dict = json.loads(content.strip())
        assert span_dict["attributes"] == {}
