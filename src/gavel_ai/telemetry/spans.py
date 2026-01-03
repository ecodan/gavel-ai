"""
OpenTelemetry setup and instrumentation for gavel-ai.

This module provides centralized tracer management for emitting spans
throughout the gavel-ai application. All modules should use get_tracer(__name__)
to obtain a tracer for their module.

Key principles:
- Spans are emitted immediately upon completion (not buffered)
- Spans written to per-run telemetry.jsonl (one JSON object per line)
- Use context managers for automatic span closing
- All spans include run_id, trace_id, and context-specific attributes
- Gracefully handles missing OT receiver (application continues)

Telemetry Export:
- Default: No-op exporter when not in a run context
- Run context: TelemetryFileExporter writes to .gavel/evaluations/{eval}/runs/{run_id}/telemetry.jsonl
- Optional: OTLP export via OTEL_EXPORTER_OTLP_ENDPOINT environment variable

Per Epic 7 Story 7.1 and logging-vs-telemetry-specification.md.

Example:
    ```python
    from gavel_ai.telemetry import get_tracer, configure_run_telemetry, reset_telemetry

    tracer = get_tracer(__name__)

    # Configure telemetry for a run
    configure_run_telemetry("run-123", "eval-name")

    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("operation.type", "processing")
        # Do work here
        # Span is automatically closed and exported when exiting context

    # Reset after run completes
    reset_telemetry()
    ```
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

# Get module logger
logger = logging.getLogger("gavel-ai")

# Global state
_tracer_provider: Optional[TracerProvider] = None
_dynamic_processor: Optional["DynamicSpanProcessor"] = None
_current_telemetry_path: Optional[Path] = None
_current_run_id: Optional[str] = None
_initialized: bool = False


class TelemetryFileExporter(SpanExporter):
    """
    Export spans to JSONL file in run directory.

    Per Architecture Decision 9: Telemetry spans written to telemetry.jsonl
    in per-run directory structure.

    Output format:
    - One JSON object per line (JSONL)
    - Each span includes: name, trace_id, span_id, parent_id, times, duration, status, attributes
    """

    def __init__(self, file_path: Path):
        """
        Initialize file exporter.

        Args:
            file_path: Path to telemetry.jsonl file
        """
        self.file_path = file_path
        # Create directory structure if doesn't exist
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """
        Export spans to JSONL file.

        Args:
            spans: Sequence of spans to export

        Returns:
            SpanExportResult.SUCCESS or SpanExportResult.FAILURE
        """
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                for span in spans:
                    span_dict = self._span_to_dict(span)
                    f.write(json.dumps(span_dict) + "\n")
            return SpanExportResult.SUCCESS
        except Exception as e:
            logger.warning(f"Failed to export spans to {self.file_path}: {e}")
            return SpanExportResult.FAILURE

    def _span_to_dict(self, span: ReadableSpan) -> Dict[str, Any]:
        """
        Convert span to dictionary for JSON serialization.

        Per logging-vs-telemetry-specification.md schema:
        - name: str
        - trace_id: str (hex)
        - span_id: str (hex)
        - parent_id: Optional[str] (hex or null)
        - start_time: int (nanoseconds since epoch)
        - end_time: int (nanoseconds since epoch)
        - duration_ns: int
        - status: str ("OK", "ERROR", "UNSET")
        - attributes: Dict[str, Any]

        Args:
            span: ReadableSpan to convert

        Returns:
            Dictionary representation of span
        """
        # Extract parent span ID
        parent_id: Optional[str] = None
        if span.parent is not None:
            parent_id = format(span.parent.span_id, "016x")

        # Convert attributes to JSON-serializable dict
        attributes: Dict[str, Any] = {}
        if span.attributes:
            for key, value in span.attributes.items():
                # Handle tuples (OT stores repeated fields as tuples)
                if isinstance(value, tuple):
                    attributes[key] = list(value)
                else:
                    attributes[key] = value

        return {
            "name": span.name,
            "trace_id": format(span.context.trace_id, "032x"),
            "span_id": format(span.context.span_id, "016x"),
            "parent_id": parent_id,
            "start_time": span.start_time,
            "end_time": span.end_time,
            "duration_ns": span.end_time - span.start_time if span.end_time else 0,
            "status": span.status.status_code.name,
            "attributes": attributes,
        }

    def shutdown(self) -> None:
        """Shutdown exporter (no-op for file exporter)."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush (no-op for file exporter - writes are immediate)."""
        return True


class NoOpSpanExporter(SpanExporter):
    """
    No-op span exporter for graceful degradation.

    Used when no run context is configured or when telemetry is disabled.
    Telemetry infrastructure remains active but spans are not exported.
    """

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """No-op export - spans are collected but not written."""
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        """No-op shutdown."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """No-op flush."""
        return True


class DynamicSpanProcessor(SpanProcessor):
    """
    Span processor that supports dynamic exporter swapping.

    This allows changing the exporter at runtime without recreating
    the TracerProvider, which OpenTelemetry doesn't allow.
    """

    def __init__(self, exporter: Optional[SpanExporter] = None):
        """
        Initialize with optional exporter.

        Args:
            exporter: Initial exporter (defaults to NoOpSpanExporter)
        """
        self._exporter: SpanExporter = exporter or NoOpSpanExporter()
        self._shutdown = False

    def set_exporter(self, exporter: SpanExporter) -> None:
        """
        Swap the current exporter.

        Args:
            exporter: New exporter to use
        """
        # Shutdown old exporter
        if self._exporter is not None:
            try:
                self._exporter.shutdown()
            except Exception as e:
                logger.warning(f"Error shutting down old exporter: {e}")

        self._exporter = exporter

    def on_start(self, span: Span, parent_context: Optional[Context] = None) -> None:
        """Called when span starts (no-op for immediate export)."""
        pass

    def on_end(self, span: ReadableSpan) -> None:
        """Called when span ends - export immediately."""
        if self._shutdown:
            return

        if self._exporter is not None:
            try:
                self._exporter.export([span])
            except Exception as e:
                logger.warning(f"Failed to export span: {e}")

    def shutdown(self) -> None:
        """Shutdown the processor."""
        self._shutdown = True
        if self._exporter is not None:
            self._exporter.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush pending spans."""
        if self._exporter is not None:
            return self._exporter.force_flush(timeout_millis)
        return True


def _get_default_exporter() -> SpanExporter:
    """
    Get the default span exporter based on environment.

    Priority:
    1. OTLP exporter if OTEL_EXPORTER_OTLP_ENDPOINT is set
    2. NoOpSpanExporter otherwise

    Returns:
        SpanExporter instance
    """
    # Check if OTLP endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            logger.debug(f"Using OTLP exporter: {otlp_endpoint}")
            return exporter
        except ImportError as e:
            logger.warning(f"OTLP exporter not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to configure OTLP exporter: {e}")

    # Default to no-op exporter
    logger.debug("Using no-op telemetry exporter (no run context)")
    return NoOpSpanExporter()


def _initialize_tracer_provider() -> TracerProvider:
    """
    Initialize the global OpenTelemetry tracer provider.

    This handles the case where OpenTelemetry may already be initialized
    by other libraries (e.g., pytest plugins). In that case, we add our
    DynamicSpanProcessor to the existing global provider.

    Returns:
        Configured TracerProvider instance
    """
    global _dynamic_processor, _initialized

    try:
        # Check if a TracerProvider is already registered globally
        existing_provider = trace.get_tracer_provider()

        # Create our dynamic processor
        _dynamic_processor = DynamicSpanProcessor(_get_default_exporter())

        # If there's already a provider (from pytest plugins, etc.),
        # try to add our processor to it
        if (
            existing_provider is not None
            and hasattr(existing_provider, "add_span_processor")
            and not isinstance(existing_provider, trace.ProxyTracerProvider)
        ):
            # Add our processor to the existing provider
            existing_provider.add_span_processor(_dynamic_processor)
            _initialized = True
            logger.debug("Added DynamicSpanProcessor to existing TracerProvider")
            return existing_provider

        # No usable existing provider - create our own
        resource = Resource.create(
            {
                "service.name": "gavel-ai",
                "service.version": "0.1.0",
            }
        )

        provider = TracerProvider(resource=resource)
        provider.add_span_processor(_dynamic_processor)

        # Try to set as global provider
        if not _initialized:
            try:
                trace.set_tracer_provider(provider)
                _initialized = True
                logger.debug("OpenTelemetry tracer provider initialized")
            except Exception:
                # Provider was already set by another library
                # Our processor won't work but app continues
                logger.debug("TracerProvider already set - using existing")
                _initialized = True

        return provider

    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")
        logger.warning("Application will continue without telemetry")
        return TracerProvider()


def configure_run_telemetry(
    run_id: str,
    eval_name: str,
    base_dir: str = ".gavel",
) -> Path:
    """
    Configure telemetry export for a specific run.

    Sets up TelemetryFileExporter to write spans to:
    {base_dir}/evaluations/{eval_name}/runs/{run_id}/telemetry.jsonl

    This function should be called at the start of an evaluation run.
    Call reset_telemetry() when the run completes.

    Args:
        run_id: Run identifier (e.g., "run-20251231-120000")
        eval_name: Evaluation name (e.g., "test_os")
        base_dir: Base directory for gavel data (default: ".gavel")

    Returns:
        Path to telemetry.jsonl file

    Example:
        ```python
        telemetry_path = configure_run_telemetry("run-123", "my_eval")
        try:
            # Execute evaluation...
            pass
        finally:
            reset_telemetry()
        ```
    """
    global _tracer_provider, _dynamic_processor, _current_telemetry_path, _current_run_id

    # Ensure tracer provider is initialized
    if _tracer_provider is None:
        _tracer_provider = _initialize_tracer_provider()

    # Create telemetry file path
    telemetry_path = Path(base_dir) / "evaluations" / eval_name / "runs" / run_id / "telemetry.jsonl"
    _current_telemetry_path = telemetry_path
    _current_run_id = run_id

    # Create new file exporter and swap it in
    file_exporter = TelemetryFileExporter(telemetry_path)
    if _dynamic_processor is not None:
        _dynamic_processor.set_exporter(file_exporter)

    logger.debug(f"Configured telemetry export: {telemetry_path}")
    return telemetry_path


def reset_telemetry() -> None:
    """
    Reset telemetry to no-op exporter after run completes.

    This function should be called after an evaluation run completes
    (whether successful or failed) to clean up run-specific telemetry.

    Example:
        ```python
        configure_run_telemetry("run-123", "my_eval")
        try:
            # Execute evaluation...
            pass
        finally:
            reset_telemetry()
        ```
    """
    global _current_telemetry_path, _dynamic_processor, _current_run_id

    _current_telemetry_path = None
    _current_run_id = None

    # Reset to default exporter
    if _dynamic_processor is not None:
        _dynamic_processor.set_exporter(_get_default_exporter())

    logger.debug("Reset telemetry to no-op exporter")


def get_current_telemetry_path() -> Optional[Path]:
    """
    Get the current telemetry file path if in a run context.

    Returns:
        Path to telemetry.jsonl if configured, None otherwise
    """
    return _current_telemetry_path


def get_current_run_id() -> Optional[str]:
    """
    Get the current run ID if in a run context.

    Returns:
        Run ID if configured, None otherwise
    """
    return _current_run_id


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance for the given module name.

    This function should be called from each module that needs to emit spans:
    ```python
    tracer = get_tracer(__name__)
    ```

    Args:
        name: Module name (typically __name__)

    Returns:
        Tracer instance configured for this module

    Example:
        ```python
        from gavel_ai.telemetry import get_tracer

        tracer = get_tracer(__name__)

        with tracer.start_as_current_span("operation_name") as span:
            span.set_attribute("key", "value")
            # Do work
        ```
    """
    global _tracer_provider

    # Initialize tracer provider if not already done
    if _tracer_provider is None:
        _tracer_provider = _initialize_tracer_provider()

    try:
        # Get tracer from global provider
        return trace.get_tracer(name)
    except Exception as e:
        logger.warning(f"Failed to get tracer for {name}: {e}")
        # Return a no-op tracer
        return trace.get_tracer("noop")


def start_span(name: str) -> trace.Span:
    """
    Start a new span with the given name.

    Convenience function for simple span creation.

    Args:
        name: Span name

    Returns:
        Context manager for the span
    """
    tracer = get_tracer(__name__)
    return tracer.start_as_current_span(name)


# Initialize tracer provider on module import
_tracer_provider = _initialize_tracer_provider()

__all__ = [
    "get_tracer",
    "start_span",
    "trace",
    "configure_run_telemetry",
    "reset_telemetry",
    "get_current_telemetry_path",
    "get_current_run_id",
    "TelemetryFileExporter",
    "NoOpSpanExporter",
    "DynamicSpanProcessor",
]
