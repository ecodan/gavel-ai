"""
OpenTelemetry setup and instrumentation for gavel-ai.

This module provides centralized tracer management for emitting spans
throughout the gavel-ai application. All modules should use get_tracer(__name__)
to obtain a tracer for their module.

Key principles:
- Spans are emitted immediately upon completion (not buffered)
- Use context managers for automatic span closing
- All spans include run_id, trace_id, and context-specific attributes
- Gracefully handles missing OT receiver (application continues)

Example:
    ```python
    from gavel_ai.telemetry import get_tracer

    tracer = get_tracer(__name__)

    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("operation.type", "processing")
        # Do work here
        # Span is automatically closed and exported when exiting context
    ```
"""

import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

# Get module logger
logger = logging.getLogger("gavel-ai")

# Global tracer provider instance
_tracer_provider: Optional[TracerProvider] = None


def _initialize_tracer_provider() -> TracerProvider:
    """
    Initialize and configure the global OpenTelemetry tracer provider.

    Creates a tracer provider with:
    - SimpleSpanProcessor for immediate emission (not buffered)
    - Console exporter for development
    - Fallback to OTLP exporter if configured
    - Graceful error handling

    Returns:
        Configured TracerProvider instance
    """
    try:
        # Create resource with service name
        resource = Resource.create(
            {
                "service.name": "gavel-ai",
                "service.version": "0.1.0",
            }
        )

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Add simple span processor for immediate emission
        # (NOT buffered - spans are exported immediately)
        processor = SimpleSpanProcessor(_get_span_exporter())

        provider.add_span_processor(processor)

        # Set as global provider
        trace.set_tracer_provider(provider)

        logger.debug("OpenTelemetry tracer provider initialized")

        return provider

    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry: {e}")
        logger.warning("Application will continue without telemetry")

        # Return a no-op provider that doesn't fail
        return TracerProvider()


def _get_span_exporter():
    """
    Get the appropriate span exporter for the environment.

    Tries OTLP exporter first (if configured), falls back to console exporter,
    and handles errors gracefully.

    Returns:
        Span exporter instance
    """
    import os

    # Check if OTLP endpoint is configured
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    if otlp_endpoint:
        try:
            # Use OTLP exporter if configured
            from opentelemetry.exporter.trace.otlp.proto.http import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            logger.debug(f"Using OTLP exporter: {otlp_endpoint}")
            return exporter
        except ImportError as e:
            logger.warning(f"OTLP exporter not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to configure OTLP exporter: {e}")

    # Fallback to console exporter for development
    try:
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter

        logger.debug("Using console span exporter")
        return ConsoleSpanExporter()
    except Exception as e:
        logger.warning(f"Failed to create console exporter: {e}")
        # Return a basic span exporter that doesn't fail
        from opentelemetry.sdk.trace.export import SpanExporter

        class NoOpSpanExporter(SpanExporter):
            """No-op span exporter for graceful degradation."""

            def export(self, spans) -> None:
                """No-op export."""
                pass

            def shutdown(self) -> None:
                """No-op shutdown."""
                pass

        return NoOpSpanExporter()


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

    Args:
        name: Span name

    Returns:
        Context manager for the span
    """
    tracer = get_tracer(__name__)
    return tracer.start_as_current_span(name)


# Initialize tracer provider on module import
_tracer_provider = _initialize_tracer_provider()

__all__ = ["get_tracer", "start_span", "trace"]
