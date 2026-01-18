"""
Unit tests for telemetry.py backward compatibility module.

This module re-exports telemetry functions from the telemetry package
for backward compatibility with existing imports.
"""

import pytest


class TestTelemetryCompatibility:
    """Test backward compatibility module re-exports."""

    def test_get_tracer_import(self):
        """get_tracer can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import get_tracer

        assert callable(get_tracer)

    def test_configure_run_telemetry_import(self):
        """configure_run_telemetry can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import configure_run_telemetry

        assert callable(configure_run_telemetry)

    def test_reset_telemetry_import(self):
        """reset_telemetry can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import reset_telemetry

        assert callable(reset_telemetry)

    def test_get_metadata_collector_import(self):
        """get_metadata_collector can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import get_metadata_collector

        assert callable(get_metadata_collector)

    def test_reset_metadata_collector_import(self):
        """reset_metadata_collector can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import reset_metadata_collector

        assert callable(reset_metadata_collector)

    def test_start_span_import(self):
        """start_span can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import start_span

        assert callable(start_span)

    def test_trace_import(self):
        """trace decorator can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import trace

        assert trace is not None

    def test_get_current_run_id_import(self):
        """get_current_run_id can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import get_current_run_id

        assert callable(get_current_run_id)

    def test_get_current_telemetry_path_import(self):
        """get_current_telemetry_path can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import get_current_telemetry_path

        assert callable(get_current_telemetry_path)

    def test_classes_import(self):
        """Telemetry classes can be imported from gavel_ai.telemetry."""
        from gavel_ai.telemetry import (
            DynamicSpanProcessor,
            LLMMetrics,
            NoOpSpanExporter,
            RunMetadataCollector,
            RunMetadataSchema,
            ScenarioTimingStats,
            TelemetryFileExporter,
        )

        assert DynamicSpanProcessor is not None
        assert LLMMetrics is not None
        assert NoOpSpanExporter is not None
        assert RunMetadataCollector is not None
        assert RunMetadataSchema is not None
        assert ScenarioTimingStats is not None
        assert TelemetryFileExporter is not None

    def test_all_exports_defined(self):
        """__all__ is defined with expected exports."""
        from gavel_ai import telemetry

        assert hasattr(telemetry, "__all__")
        assert "get_tracer" in telemetry.__all__
        assert "configure_run_telemetry" in telemetry.__all__
        assert "reset_telemetry" in telemetry.__all__
        assert "get_metadata_collector" in telemetry.__all__

    def test_backward_compatibility_with_cli_common(self):
        """Backward compatibility: cli.common can import from telemetry."""
        # This simulates how cli/common.py imports get_tracer
        from gavel_ai.telemetry import get_tracer

        # Should not raise ImportError
        assert callable(get_tracer)
        tracer = get_tracer("test_module")
        assert tracer is not None
