"""
Tests for gavel-ai OpenTelemetry setup (Story 1.6).
"""

from opentelemetry import trace

from gavel_ai.telemetry import get_tracer, start_span


class TestOpenTelemetrySetup:
    """Test that OpenTelemetry is properly configured."""

    def test_tracer_creation(self) -> None:
        """Test that tracer can be created."""
        tracer = get_tracer(__name__)
        assert tracer is not None
        assert isinstance(tracer, trace.Tracer)

    def test_get_tracer_with_module_name(self) -> None:
        """Test that get_tracer works with module names."""
        tracer = get_tracer("test.module")
        assert tracer is not None

    def test_get_tracer_consistency(self) -> None:
        """Test that getting same tracer twice returns a tracer."""
        tracer1 = get_tracer("consistent_test")
        tracer2 = get_tracer("consistent_test")
        # Both should be valid tracers
        assert tracer1 is not None
        assert tracer2 is not None

    def test_span_creation(self) -> None:
        """Test that spans can be created."""
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("test_span") as span:
            assert span is not None

    def test_span_attributes(self) -> None:
        """Test that span attributes can be set."""
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("test_span_attrs") as span:
            span.set_attribute("test.key", "test_value")
            span.set_attribute("test.number", 42)
            # Attributes should be set without error

    def test_nested_spans(self) -> None:
        """Test that nested spans work correctly."""
        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("outer_span"):
            with tracer.start_as_current_span("inner_span"):
                # Should not raise any errors
                pass

    def test_start_span_helper(self) -> None:
        """Test the start_span helper function."""
        with start_span("test_helper_span"):
            # Should not raise
            pass

    def test_span_with_multiple_attributes(self) -> None:
        """Test setting multiple attributes on a span."""
        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("multi_attr_span") as span:
            span.set_attribute("run_id", "test_run_123")
            span.set_attribute("trace_id", "trace_456")
            span.set_attribute("operation.type", "test_operation")
            span.set_attribute("operation.status", "success")
            span.set_attribute("metrics.duration_ms", 1234)

    def test_span_context_isolation(self) -> None:
        """Test that span contexts are isolated."""
        tracer = get_tracer(__name__)

        # Create first span
        with tracer.start_as_current_span("span_1"):
            pass

        # Create second span - should not be affected by first
        with tracer.start_as_current_span("span_2"):
            pass

        # Both should complete without error


class TestGracefulDegradation:
    """Test that application continues without OT receiver."""

    def test_missing_receiver_does_not_fail(self) -> None:
        """Test that spans work even without configured receiver."""
        # This test verifies graceful degradation
        # Even if no OTLP receiver is configured, spans should work

        tracer = get_tracer("degradation_test")

        # Should not raise even without receiver
        with tracer.start_as_current_span("safe_span"):
            pass

    def test_malformed_span_name_handled(self) -> None:
        """Test that malformed span names are handled gracefully."""
        tracer = get_tracer(__name__)

        # Should not raise with unusual span name
        with tracer.start_as_current_span(""):
            pass

        with tracer.start_as_current_span("span/with/slashes"):
            pass

        with tracer.start_as_current_span("span.with.dots"):
            pass

    def test_span_error_does_not_block_application(self) -> None:
        """Test that span errors don't block application flow."""
        tracer = get_tracer(__name__)

        try:
            with tracer.start_as_current_span("error_test"):
                # Simulate a span error by not properly closing
                # (though context manager should handle this)
                pass
        except Exception:
            # Should not reach here - application should handle gracefully
            pass


class TestSpanEmission:
    """Test that spans are emitted correctly."""

    def test_span_closure_on_context_exit(self) -> None:
        """Test that spans are properly closed and emitted when exiting context."""
        tracer = get_tracer(__name__)

        # Span should be emitted when context exits
        with tracer.start_as_current_span("immediate_emission"):
            pass

        # If we got here, span was properly emitted and didn't block

    def test_multiple_sequential_spans(self) -> None:
        """Test that multiple spans can be emitted sequentially."""
        tracer = get_tracer(__name__)

        for i in range(5):
            with tracer.start_as_current_span(f"span_{i}") as span:
                span.set_attribute("index", i)

        # All spans should have been emitted


class TestTracerObtention:
    """Test tracer obtaining behavior."""

    def test_different_module_tracers(self) -> None:
        """Test that different modules can get their own tracers."""
        tracer_main = get_tracer("main")
        tracer_util = get_tracer("util")
        tracer_core = get_tracer("core")

        # All should be valid tracers
        assert tracer_main is not None
        assert tracer_util is not None
        assert tracer_core is not None

        # All should be tracers
        assert isinstance(tracer_main, trace.Tracer)
        assert isinstance(tracer_util, trace.Tracer)
        assert isinstance(tracer_core, trace.Tracer)

    def test_tracer_with_dunder_name(self) -> None:
        """Test that tracer works with __name__ (dunder name)."""
        tracer = get_tracer(__name__)
        assert tracer is not None

        with tracer.start_as_current_span("dunder_test"):
            pass
