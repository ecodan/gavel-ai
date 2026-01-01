"""
Telemetry module for gavel-ai.

Provides OpenTelemetry span collection and run metadata aggregation.
"""

# Import from spans module
from gavel_ai.telemetry.spans import (
    DynamicSpanProcessor,
    NoOpSpanExporter,
    TelemetryFileExporter,
    configure_run_telemetry,
    get_current_telemetry_path,
    get_tracer,
    reset_telemetry,
    start_span,
    trace,
)

# Import from metadata module
from gavel_ai.telemetry.metadata import (
    LLMMetrics,
    RunMetadataCollector,
    RunMetadataSchema,
    ScenarioTimingStats,
    get_metadata_collector,
    reset_metadata_collector,
)

__all__ = [
    # Span collection and export (Story 7.1)
    "get_tracer",
    "start_span",
    "trace",
    "configure_run_telemetry",
    "reset_telemetry",
    "get_current_telemetry_path",
    "TelemetryFileExporter",
    "NoOpSpanExporter",
    "DynamicSpanProcessor",
    # Run metadata collection and aggregation (Story 7.2)
    "ScenarioTimingStats",
    "LLMMetrics",
    "RunMetadataSchema",
    "RunMetadataCollector",
    "get_metadata_collector",
    "reset_metadata_collector",
]
