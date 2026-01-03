"""
Backward compatibility module for telemetry imports.

This module maintains compatibility with existing imports:
    from gavel_ai.telemetry import get_tracer, configure_run_telemetry, etc.

The actual implementation has been moved to gavel_ai.telemetry package (spans.py, metadata.py).
"""

# Re-export everything from the telemetry package for backward compatibility
from gavel_ai.telemetry import (  # noqa: F401
    DynamicSpanProcessor,
    LLMMetrics,
    NoOpSpanExporter,
    RunMetadataCollector,
    RunMetadataSchema,
    ScenarioTimingStats,
    TelemetryFileExporter,
    configure_run_telemetry,
    get_current_run_id,
    get_current_telemetry_path,
    get_metadata_collector,
    get_tracer,
    reset_metadata_collector,
    reset_telemetry,
    start_span,
    trace,
)

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
    "ScenarioTimingStats",
    "LLMMetrics",
    "RunMetadataSchema",
    "RunMetadataCollector",
    "get_metadata_collector",
    "reset_metadata_collector",
]
