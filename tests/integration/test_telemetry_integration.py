"""
Integration tests for telemetry collection and export.

Per Story 7.1: End-to-end telemetry tests verifying spans are captured
with correct attributes during evaluation runs.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from gavel_ai.telemetry import (
    configure_run_telemetry,
    get_tracer,
    reset_telemetry,
)


class TestTelemetryEndToEnd:
    """End-to-end tests for telemetry collection."""

    @pytest.fixture(autouse=True)
    def cleanup_telemetry(self):
        """Ensure telemetry is reset after each test."""
        yield
        reset_telemetry()

    def _read_telemetry_file(self, path: Path) -> List[Dict[str, Any]]:
        """Read and parse telemetry JSONL file."""
        if not path.exists():
            return []
        lines = path.read_text().strip().split("\n")
        return [json.loads(line) for line in lines if line]

    def test_telemetry_file_created_on_configure(self, tmp_path: Path) -> None:
        """Telemetry file is created when run context is configured."""
        telemetry_path = configure_run_telemetry(
            run_id="run-test",
            eval_name="test_eval",
            base_dir=str(tmp_path),
        )

        # Create a span to trigger file creation
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("test.span"):
            pass

        assert telemetry_path.exists()
        assert telemetry_path.suffix == ".jsonl"

    def test_span_schema_complete(self, tmp_path: Path) -> None:
        """Exported spans have complete schema per specification."""
        telemetry_path = configure_run_telemetry(
            run_id="run-schema-test",
            eval_name="eval",
            base_dir=str(tmp_path),
        )

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("schema.test.span") as span:
            span.set_attribute("test.attr", "test_value")

        spans = self._read_telemetry_file(telemetry_path)
        assert len(spans) == 1

        span_data = spans[0]

        # Verify all required fields present
        required_fields = [
            "name",
            "trace_id",
            "span_id",
            "parent_id",
            "start_time",
            "end_time",
            "duration_ns",
            "status",
            "attributes",
        ]
        for field in required_fields:
            assert field in span_data, f"Missing field: {field}"

        # Verify field types
        assert isinstance(span_data["name"], str)
        assert isinstance(span_data["trace_id"], str)
        assert isinstance(span_data["span_id"], str)
        assert span_data["parent_id"] is None or isinstance(span_data["parent_id"], str)
        assert isinstance(span_data["start_time"], int)
        assert isinstance(span_data["end_time"], int)
        assert isinstance(span_data["duration_ns"], int)
        assert isinstance(span_data["status"], str)
        assert isinstance(span_data["attributes"], dict)

        # Verify hex format for IDs
        assert len(span_data["trace_id"]) == 32  # 128 bits = 32 hex chars
        assert len(span_data["span_id"]) == 16  # 64 bits = 16 hex chars

    def test_run_id_captured_in_attributes(self, tmp_path: Path) -> None:
        """Spans include run_id attribute when code explicitly sets it."""
        from gavel_ai.telemetry import get_current_run_id

        run_id = "run-12345"
        telemetry_path = configure_run_telemetry(
            run_id=run_id,
            eval_name="eval",
            base_dir=str(tmp_path),
        )

        # Verify get_current_run_id returns the configured value
        assert get_current_run_id() == run_id

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("test.span") as span:
            # Simulate what instrumented code does: get run_id and set attribute
            current_run_id = get_current_run_id()
            if current_run_id:
                span.set_attribute("run_id", current_run_id)
            span.set_attribute("custom.attr", "value")

        spans = self._read_telemetry_file(telemetry_path)
        assert len(spans) == 1
        assert "run_id" in spans[0]["attributes"]
        assert spans[0]["attributes"]["run_id"] == run_id

    def test_nested_spans_have_parent_id(self, tmp_path: Path) -> None:
        """Nested spans correctly reference parent spans."""
        telemetry_path = configure_run_telemetry(
            run_id="run-nested",
            eval_name="eval",
            base_dir=str(tmp_path),
        )

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("parent.span") as parent:
            with tracer.start_as_current_span("child.span") as child:
                pass

        spans = self._read_telemetry_file(telemetry_path)
        assert len(spans) == 2

        # Find parent and child spans
        parent_span = next(s for s in spans if s["name"] == "parent.span")
        child_span = next(s for s in spans if s["name"] == "child.span")

        # Parent has no parent (root span)
        assert parent_span["parent_id"] is None

        # Child references parent
        assert child_span["parent_id"] == parent_span["span_id"]

    def test_duration_calculated_correctly(self, tmp_path: Path) -> None:
        """Span duration_ns is correctly calculated."""
        telemetry_path = configure_run_telemetry(
            run_id="run-duration",
            eval_name="eval",
            base_dir=str(tmp_path),
        )

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("duration.span"):
            # Small delay to ensure measurable duration
            import time

            time.sleep(0.01)  # 10ms

        spans = self._read_telemetry_file(telemetry_path)
        assert len(spans) == 1

        span_data = spans[0]
        calculated_duration = span_data["end_time"] - span_data["start_time"]
        assert span_data["duration_ns"] == calculated_duration
        assert span_data["duration_ns"] > 0

    def test_attributes_preserved(self, tmp_path: Path) -> None:
        """Span attributes are preserved in export."""
        telemetry_path = configure_run_telemetry(
            run_id="run-attrs",
            eval_name="eval",
            base_dir=str(tmp_path),
        )

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("attr.span") as span:
            span.set_attribute("llm.provider", "anthropic")
            span.set_attribute("llm.model", "claude-3-5-sonnet")
            span.set_attribute("llm.tokens.prompt", 150)
            span.set_attribute("llm.tokens.completion", 100)
            span.set_attribute("llm.latency_ms", 2333)

        spans = self._read_telemetry_file(telemetry_path)
        attrs = spans[0]["attributes"]

        assert attrs["llm.provider"] == "anthropic"
        assert attrs["llm.model"] == "claude-3-5-sonnet"
        assert attrs["llm.tokens.prompt"] == 150
        assert attrs["llm.tokens.completion"] == 100
        assert attrs["llm.latency_ms"] == 2333

    def test_multiple_spans_in_sequence(self, tmp_path: Path) -> None:
        """Multiple spans are correctly captured in sequence."""
        telemetry_path = configure_run_telemetry(
            run_id="run-sequence",
            eval_name="eval",
            base_dir=str(tmp_path),
        )

        tracer = get_tracer(__name__)

        # Create multiple spans
        for i in range(5):
            with tracer.start_as_current_span(f"sequence.span.{i}") as span:
                span.set_attribute("sequence.index", i)

        spans = self._read_telemetry_file(telemetry_path)
        assert len(spans) == 5

        # Verify sequence
        for i, span_data in enumerate(spans):
            assert span_data["name"] == f"sequence.span.{i}"
            assert span_data["attributes"]["sequence.index"] == i

    def test_tracer_from_different_modules(self, tmp_path: Path) -> None:
        """Tracers from different modules all write to same telemetry file."""
        telemetry_path = configure_run_telemetry(
            run_id="run-modules",
            eval_name="eval",
            base_dir=str(tmp_path),
        )

        # Get tracers with different module names
        tracer1 = get_tracer("module.one")
        tracer2 = get_tracer("module.two")
        tracer3 = get_tracer("module.three")

        with tracer1.start_as_current_span("span.from.module1"):
            pass
        with tracer2.start_as_current_span("span.from.module2"):
            pass
        with tracer3.start_as_current_span("span.from.module3"):
            pass

        spans = self._read_telemetry_file(telemetry_path)
        assert len(spans) == 3

        span_names = {s["name"] for s in spans}
        assert span_names == {"span.from.module1", "span.from.module2", "span.from.module3"}

    def test_scenario_ids_captured_in_batch(self, tmp_path: Path) -> None:
        """Batch spans include scenario.ids attribute with list of processed IDs."""
        telemetry_path = configure_run_telemetry(
            run_id="run-batch",
            eval_name="eval",
            base_dir=str(tmp_path),
        )

        tracer = get_tracer(__name__)
        scenario_list = ["scenario-1", "scenario-2", "scenario-3"]

        # Simulate a processor batch span
        with tracer.start_as_current_span("processor.execute") as span:
            span.set_attribute("processor.type", "prompt_input")
            span.set_attribute("scenario.ids", scenario_list)
            span.set_attribute("input.count", len(scenario_list))

        spans = self._read_telemetry_file(telemetry_path)
        assert len(spans) == 1
        assert "scenario.ids" in spans[0]["attributes"]
        assert spans[0]["attributes"]["scenario.ids"] == scenario_list


class TestTelemetryRunDirectory:
    """Tests for telemetry file directory structure."""

    @pytest.fixture(autouse=True)
    def cleanup_telemetry(self):
        """Ensure telemetry is reset after each test."""
        yield
        reset_telemetry()

    def test_telemetry_in_correct_run_directory(self, tmp_path: Path) -> None:
        """Telemetry file is in the correct run directory structure."""
        telemetry_path = configure_run_telemetry(
            run_id="run-20251231-120000",
            eval_name="my_evaluation",
            base_dir=str(tmp_path),
        )

        # Create a span to ensure file is created
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("test"):
            pass

        expected = (
            tmp_path
            / "evaluations"
            / "my_evaluation"
            / "runs"
            / "run-20251231-120000"
            / "telemetry.jsonl"
        )
        assert telemetry_path == expected
        assert telemetry_path.exists()

    def test_different_eval_names_create_different_paths(self, tmp_path: Path) -> None:
        """Different evaluation names create different telemetry paths."""
        path1 = configure_run_telemetry(
            run_id="run-1",
            eval_name="eval_a",
            base_dir=str(tmp_path),
        )
        reset_telemetry()

        path2 = configure_run_telemetry(
            run_id="run-1",
            eval_name="eval_b",
            base_dir=str(tmp_path),
        )

        assert path1 != path2
        assert "eval_a" in str(path1)
        assert "eval_b" in str(path2)

    def test_custom_base_dir(self, tmp_path: Path) -> None:
        """Custom base_dir is used for telemetry path."""
        custom_base = tmp_path / "custom_gavel_dir"

        telemetry_path = configure_run_telemetry(
            run_id="run-custom",
            eval_name="eval",
            base_dir=str(custom_base),
        )

        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("test"):
            pass

        assert str(custom_base) in str(telemetry_path)
        assert telemetry_path.exists()
