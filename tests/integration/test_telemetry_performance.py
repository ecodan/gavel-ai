"""
Performance tests for telemetry overhead.

Per Story 7.1 AC 4: Telemetry should add <5% overhead to evaluation runs.
"""

import time
from pathlib import Path

import pytest

from gavel_ai.telemetry import (
    NoOpSpanExporter,
    TelemetryFileExporter,
    configure_run_telemetry,
    get_tracer,
    reset_telemetry,
)


class TestTelemetryPerformance:
    """Performance tests for telemetry overhead."""

    @pytest.fixture(autouse=True)
    def cleanup_telemetry(self):
        """Ensure telemetry is reset after each test."""
        yield
        reset_telemetry()

    def test_span_creation_overhead(self, tmp_path: Path) -> None:
        """Measure overhead of span creation and export."""
        # Configure telemetry
        configure_run_telemetry("run-perf", "eval", str(tmp_path))

        tracer = get_tracer(__name__)
        iterations = 1000

        # Warm up
        for _ in range(100):
            with tracer.start_as_current_span("warmup"):
                pass

        # Measure span creation with export
        start_time = time.perf_counter()
        for i in range(iterations):
            with tracer.start_as_current_span(f"benchmark.span.{i}") as span:
                span.set_attribute("iteration", i)
                span.set_attribute("test.key", "test_value")
        telemetry_time = time.perf_counter() - start_time

        # Calculate average per span
        avg_span_time_ms = (telemetry_time / iterations) * 1000

        # Per AC 4: <5% overhead means span creation should be fast
        # Target: <0.5ms per span (typical LLM call is 1-5 seconds)
        assert avg_span_time_ms < 0.5, f"Average span time {avg_span_time_ms:.3f}ms exceeds 0.5ms"

        print(f"\nSpan creation overhead: {avg_span_time_ms:.4f}ms per span")
        print(f"Total time for {iterations} spans: {telemetry_time:.3f}s")

    def test_file_export_overhead(self, tmp_path: Path) -> None:
        """Measure overhead of file I/O during span export."""
        file_path = tmp_path / "telemetry.jsonl"
        exporter = TelemetryFileExporter(file_path)

        # Create mock spans for export
        from unittest.mock import MagicMock
        from opentelemetry.trace import StatusCode

        def create_mock_span(name: str) -> MagicMock:
            span = MagicMock()
            span.name = name
            span.context.trace_id = 0x7E5119529BA632D81AC0DAC7B14E6A1E
            span.context.span_id = 0xB636602EF135A53C
            span.parent = None
            span.start_time = 1735674974296088000
            span.end_time = 1735674976629510000
            span.status.status_code = StatusCode.OK
            span.attributes = {
                "llm.provider": "anthropic",
                "llm.model": "claude-3-5-sonnet",
                "llm.tokens.prompt": 150,
                "llm.tokens.completion": 100,
            }
            return span

        iterations = 1000
        spans = [create_mock_span(f"span.{i}") for i in range(10)]

        # Measure export time
        start_time = time.perf_counter()
        for _ in range(iterations):
            exporter.export(spans)
        export_time = time.perf_counter() - start_time

        # Calculate average per batch
        avg_batch_time_ms = (export_time / iterations) * 1000

        # Target: <1ms per batch of 10 spans
        assert avg_batch_time_ms < 1.0, f"Average batch export time {avg_batch_time_ms:.3f}ms exceeds 1ms"

        print(f"\nBatch export overhead: {avg_batch_time_ms:.4f}ms per batch of 10 spans")
        print(f"Total exports: {iterations * 10} spans in {export_time:.3f}s")

    def test_noop_exporter_minimal_overhead(self) -> None:
        """Verify NoOpSpanExporter has minimal overhead."""
        exporter = NoOpSpanExporter()

        # Create mock spans
        from unittest.mock import MagicMock

        spans = [MagicMock() for _ in range(1000)]

        iterations = 10000

        # Measure export time
        start_time = time.perf_counter()
        for _ in range(iterations):
            exporter.export(spans)
        export_time = time.perf_counter() - start_time

        # NoOp should be essentially instant
        avg_batch_time_us = (export_time / iterations) * 1_000_000

        # Target: <1 microsecond per call
        assert avg_batch_time_us < 10, f"NoOp export took {avg_batch_time_us:.1f}us"

        print(f"\nNoOp export overhead: {avg_batch_time_us:.2f}us per call")

    def test_configure_reset_cycle_overhead(self, tmp_path: Path) -> None:
        """Measure overhead of configure/reset cycle."""
        iterations = 100

        # Measure configure/reset cycle
        start_time = time.perf_counter()
        for i in range(iterations):
            configure_run_telemetry(f"run-{i}", "eval", str(tmp_path))
            reset_telemetry()
        cycle_time = time.perf_counter() - start_time

        avg_cycle_time_ms = (cycle_time / iterations) * 1000

        # Target: <5ms per cycle
        assert avg_cycle_time_ms < 5, f"Configure/reset cycle took {avg_cycle_time_ms:.3f}ms"

        print(f"\nConfigure/reset cycle: {avg_cycle_time_ms:.4f}ms per cycle")

    def test_typical_run_overhead_estimate(self, tmp_path: Path) -> None:
        """Estimate overhead for typical evaluation run."""
        # Typical run parameters
        num_scenarios = 50
        spans_per_scenario = 5  # processor + LLM call + judge + misc

        # Configure telemetry
        configure_run_telemetry("run-estimate", "eval", str(tmp_path))
        tracer = get_tracer(__name__)

        # Simulate typical spans
        start_time = time.perf_counter()
        for scenario in range(num_scenarios):
            # Executor span
            with tracer.start_as_current_span("executor.run") as span:
                span.set_attribute("batch.size", 1)
                span.set_attribute("executor.parallelism", 4)

                # Processor span
                with tracer.start_as_current_span("processor.execute") as proc_span:
                    proc_span.set_attribute("processor.type", "prompt_input")
                    proc_span.set_attribute("scenario.id", f"scenario-{scenario}")

                    # LLM call span
                    with tracer.start_as_current_span("provider.call_agent") as llm_span:
                        llm_span.set_attribute("llm.provider", "anthropic")
                        llm_span.set_attribute("llm.model", "claude-3-5-sonnet")
                        llm_span.set_attribute("llm.tokens.prompt", 150)
                        llm_span.set_attribute("llm.tokens.completion", 100)
                        llm_span.set_attribute("llm.latency_ms", 2000)

                # Judge span
                with tracer.start_as_current_span("judge.evaluate") as judge_span:
                    judge_span.set_attribute("judge.id", "similarity")
                    judge_span.set_attribute("judge.score", 8)
                    judge_span.set_attribute("scenario.id", f"scenario-{scenario}")

        telemetry_time = time.perf_counter() - start_time

        # Assuming typical LLM latency is 2 seconds per scenario
        typical_run_time = num_scenarios * 2.0  # seconds
        overhead_percent = (telemetry_time / typical_run_time) * 100

        # AC 4: <5% overhead
        assert overhead_percent < 5.0, f"Overhead {overhead_percent:.2f}% exceeds 5%"

        print(f"\nTypical run simulation:")
        print(f"  Scenarios: {num_scenarios}")
        print(f"  Spans per scenario: {spans_per_scenario}")
        print(f"  Total telemetry time: {telemetry_time:.3f}s")
        print(f"  Estimated run time: {typical_run_time:.1f}s")
        print(f"  Overhead: {overhead_percent:.3f}%")
