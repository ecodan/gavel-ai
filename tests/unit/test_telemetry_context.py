"""
Unit tests for telemetry context management.

Per Story 7.1: Tests for configure_run_telemetry and reset_telemetry.
"""

from pathlib import Path

import pytest

from gavel_ai.telemetry import (
    NoOpSpanExporter,
    TelemetryFileExporter,
    configure_run_telemetry,
    get_current_run_id,
    get_current_telemetry_path,
    get_tracer,
    reset_telemetry,
)


class TestConfigureRunTelemetry:
    """Tests for configure_run_telemetry function."""

    def test_configure_returns_telemetry_path(self, tmp_path: Path) -> None:
        """configure_run_telemetry returns correct telemetry file path."""
        try:
            telemetry_path = configure_run_telemetry(
                run_id="run-20251231-120000",
                eval_name="test_eval",
                base_dir=str(tmp_path),
            )

            expected_path = (
                tmp_path / "evaluations" / "test_eval" / "runs" / "run-20251231-120000" / "telemetry.jsonl"
            )
            assert telemetry_path == expected_path
        finally:
            reset_telemetry()

    def test_configure_creates_directory_structure(self, tmp_path: Path) -> None:
        """configure_run_telemetry creates directory structure."""
        try:
            telemetry_path = configure_run_telemetry(
                run_id="run-test",
                eval_name="eval-name",
                base_dir=str(tmp_path),
            )

            # Directory should be created (by TelemetryFileExporter)
            assert telemetry_path.parent.exists()
        finally:
            reset_telemetry()

    def test_get_current_telemetry_path_when_configured(self, tmp_path: Path) -> None:
        """get_current_telemetry_path returns path when run context is active."""
        try:
            configure_run_telemetry(
                run_id="run-123",
                eval_name="eval",
                base_dir=str(tmp_path),
            )

            path = get_current_telemetry_path()
            assert path is not None
            assert path.name == "telemetry.jsonl"
        finally:
            reset_telemetry()

    def test_get_current_telemetry_path_when_not_configured(self) -> None:
        """get_current_telemetry_path returns None when no run context."""
        # Make sure we're reset
        reset_telemetry()

        path = get_current_telemetry_path()
        assert path is None


class TestResetTelemetry:
    """Tests for reset_telemetry function."""

    def test_reset_clears_telemetry_path(self, tmp_path: Path) -> None:
        """reset_telemetry clears the current telemetry path."""
        try:
            configure_run_telemetry(
                run_id="run-to-reset",
                eval_name="eval",
                base_dir=str(tmp_path),
            )

            # Should have path now
            assert get_current_telemetry_path() is not None

            # Reset
            reset_telemetry()

            # Path should be cleared
            assert get_current_telemetry_path() is None
        finally:
            reset_telemetry()

    def test_reset_multiple_times_safe(self) -> None:
        """Calling reset_telemetry multiple times doesn't raise."""
        # Should not raise even when already reset
        reset_telemetry()
        reset_telemetry()
        reset_telemetry()


class TestTelemetryContextIntegration:
    """Integration tests for telemetry context workflow."""

    def test_spans_exported_during_run_context(self, tmp_path: Path) -> None:
        """Spans are exported to file during active run context."""
        try:
            telemetry_path = configure_run_telemetry(
                run_id="run-span-test",
                eval_name="span_eval",
                base_dir=str(tmp_path),
            )

            # Create a span
            tracer = get_tracer(__name__)
            with tracer.start_as_current_span("test.integration.span") as span:
                span.set_attribute("test.key", "test_value")

            # Verify file was created and contains span
            assert telemetry_path.exists()
            content = telemetry_path.read_text()
            assert "test.integration.span" in content
            assert "test_value" in content
        finally:
            reset_telemetry()

    def test_multiple_runs_create_separate_files(self, tmp_path: Path) -> None:
        """Multiple runs create separate telemetry files."""
        try:
            # First run
            path1 = configure_run_telemetry(
                run_id="run-1",
                eval_name="eval",
                base_dir=str(tmp_path),
            )

            tracer = get_tracer(__name__)
            with tracer.start_as_current_span("span.run.1"):
                pass

            reset_telemetry()

            # Second run
            path2 = configure_run_telemetry(
                run_id="run-2",
                eval_name="eval",
                base_dir=str(tmp_path),
            )

            with tracer.start_as_current_span("span.run.2"):
                pass

            # Verify separate files
            assert path1 != path2
            assert path1.exists()
            assert path2.exists()

            # Verify content is in correct files
            assert "span.run.1" in path1.read_text()
            assert "span.run.2" in path2.read_text()
        finally:
            reset_telemetry()

    def test_spans_not_exported_after_reset(self, tmp_path: Path) -> None:
        """Spans are not exported after reset_telemetry."""
        try:
            telemetry_path = configure_run_telemetry(
                run_id="run-reset-test",
                eval_name="eval",
                base_dir=str(tmp_path),
            )

            tracer = get_tracer(__name__)

            # Create span during run context
            with tracer.start_as_current_span("span.during.run"):
                pass

            content_before_reset = telemetry_path.read_text()

            # Reset
            reset_telemetry()

            # Create span after reset (should go to no-op exporter)
            with tracer.start_as_current_span("span.after.reset"):
                pass

            # File should not have the post-reset span
            content_after_reset = telemetry_path.read_text()
            assert content_before_reset == content_after_reset
            assert "span.during.run" in content_after_reset
            assert "span.after.reset" not in content_after_reset
        finally:
            reset_telemetry()


class TestNoOpSpanExporter:
    """Tests for NoOpSpanExporter class."""

    def test_export_returns_success(self) -> None:
        """No-op exporter always returns SUCCESS."""
        from unittest.mock import MagicMock

        exporter = NoOpSpanExporter()

        # Create mock spans
        spans = [MagicMock(), MagicMock()]

        from opentelemetry.sdk.trace.export import SpanExportResult

        result = exporter.export(spans)
        assert result == SpanExportResult.SUCCESS

    def test_shutdown_is_noop(self) -> None:
        """Shutdown doesn't raise."""
        exporter = NoOpSpanExporter()
        exporter.shutdown()

    def test_force_flush_returns_true(self) -> None:
        """Force flush returns True."""
        exporter = NoOpSpanExporter()
        assert exporter.force_flush() is True


class TestGetCurrentRunId:
    """Tests for get_current_run_id function."""

    def test_get_current_run_id_when_configured(self, tmp_path: Path) -> None:
        """get_current_run_id returns run_id when configured."""
        try:
            run_id = "run-test-12345"
            configure_run_telemetry(
                run_id=run_id,
                eval_name="test_eval",
                base_dir=str(tmp_path),
            )

            assert get_current_run_id() == run_id
        finally:
            reset_telemetry()

    def test_get_current_run_id_when_not_configured(self) -> None:
        """get_current_run_id returns None when not configured."""
        try:
            reset_telemetry()
            assert get_current_run_id() is None
        finally:
            reset_telemetry()

    def test_get_current_run_id_after_reset(self, tmp_path: Path) -> None:
        """get_current_run_id returns None after reset_telemetry."""
        try:
            configure_run_telemetry(
                run_id="run-temp",
                eval_name="eval",
                base_dir=str(tmp_path),
            )
            assert get_current_run_id() == "run-temp"

            reset_telemetry()
            assert get_current_run_id() is None
        finally:
            reset_telemetry()
