"""
Integration tests for run metadata collection and export.

Per Story 7.2 Task 9: End-to-end tests for metadata system.
"""

import json
from pathlib import Path

import pytest

from gavel_ai.telemetry.metadata import (
    get_metadata_collector,
    reset_metadata_collector,
)


class TestMetadataIntegration:
    """Integration tests for metadata collection system."""

    def test_metadata_collector_global_instance(self) -> None:
        """Global metadata collector instance persists across calls."""
        # Reset to clean state
        reset_metadata_collector()
        
        # Get collector and record data
        collector1 = get_metadata_collector()
        collector1.record_llm_call("claude-3-5-sonnet", 100, 50)
        
        # Get collector again - should be same instance
        collector2 = get_metadata_collector()
        assert collector2 is collector1
        assert len(collector2.llm_calls) == 1

    def test_metadata_collector_reset(self) -> None:
        """reset_metadata_collector clears global state."""
        # Reset to clean state first
        reset_metadata_collector()

        # Get collector and record data
        collector = get_metadata_collector()
        initial_calls = len(collector.llm_calls)

        collector.record_llm_call("claude-3-5-sonnet", 100, 50)
        assert len(collector.llm_calls) == initial_calls + 1

        # Reset
        reset_metadata_collector()

        # Get new collector - should be empty
        new_collector = get_metadata_collector()
        assert len(new_collector.llm_calls) == 0
        assert new_collector is not collector

    def test_metadata_export_to_json(self, tmp_path: Path) -> None:
        """Metadata can be exported to JSON file."""
        # Reset and initialize collector
        reset_metadata_collector()
        collector = get_metadata_collector()
        
        # Record some data
        collector.record_run_start()
        
        collector.record_scenario_start("scenario_1")
        collector.record_llm_call("claude-3-5-sonnet", 100, 50)
        collector.record_scenario_complete("scenario_1", success=True)
        
        collector.record_scenario_start("scenario_2")
        collector.record_llm_call("gpt-4", 200, 100)
        collector.record_scenario_complete("scenario_2", success=False)
        collector.record_retry("scenario_2")
        
        collector.record_run_end()
        
        # Generate statistics
        stats = collector.compute_statistics("run-123", "test_eval")
        
        # Export to JSON
        export_file = tmp_path / "run_metadata.json"
        with open(export_file, "w", encoding="utf-8") as f:
            f.write(stats.model_dump_json(indent=2))
        
        # Verify file was created and contains valid JSON
        assert export_file.exists()
        with open(export_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Verify structure
        assert data["run_id"] == "run-123"
        assert data["eval_name"] == "test_eval"
        assert data["scenario_timing"]["count"] == 2
        assert data["llm_calls"]["total"] == 2
        assert data["execution"]["completed"] == 1
        assert data["execution"]["failed"] == 1
        assert data["execution"]["retries"] == 1

    def test_metadata_collector_multiple_models(self) -> None:
        """Token counts are aggregated correctly per model."""
        reset_metadata_collector()
        collector = get_metadata_collector()
        
        collector.record_run_start()
        
        # Multiple calls to same model
        collector.record_llm_call("claude-3-5-sonnet", 100, 50)
        collector.record_llm_call("claude-3-5-sonnet", 150, 75)
        
        # Multiple calls to different model
        collector.record_llm_call("gpt-4", 200, 100)
        
        collector.record_run_end()
        
        stats = collector.compute_statistics("run-123", "test_eval")
        
        # Verify aggregation
        assert stats.llm_calls.total == 3
        assert stats.llm_calls.by_model["claude-3-5-sonnet"] == 2
        assert stats.llm_calls.by_model["gpt-4"] == 1
        
        # Verify per-model tokens
        claude_tokens = stats.llm_calls.tokens["by_model"]["claude-3-5-sonnet"]
        assert claude_tokens["prompt"] == 250
        assert claude_tokens["completion"] == 125
        
        gpt_tokens = stats.llm_calls.tokens["by_model"]["gpt-4"]
        assert gpt_tokens["prompt"] == 200
        assert gpt_tokens["completion"] == 100

    def test_metadata_with_zero_tokens(self) -> None:
        """Metadata handles zero token counts gracefully."""
        reset_metadata_collector()
        collector = get_metadata_collector()
        
        collector.record_run_start()
        
        # Record call with zero tokens (local model, no token counting)
        collector.record_scenario_start("scenario_1")
        collector.record_llm_call("ollama-local", 0, 0)
        collector.record_scenario_complete("scenario_1", success=True)
        
        collector.record_run_end()
        
        stats = collector.compute_statistics("run-123", "test_eval")
        
        assert stats.llm_calls.total == 1
        assert stats.llm_calls.tokens["prompt_total"] == 0
        assert stats.llm_calls.tokens["completion_total"] == 0

    def test_metadata_execution_summary_accuracy(self) -> None:
        """Execution summary counts are accurate."""
        reset_metadata_collector()
        collector = get_metadata_collector()
        
        collector.record_run_start()
        
        # 5 successful scenarios
        for i in range(5):
            collector.record_scenario_start(f"scenario_{i}")
            collector.record_scenario_complete(f"scenario_{i}", success=True)
        
        # 3 failed scenarios
        for i in range(5, 8):
            collector.record_scenario_start(f"scenario_{i}")
            collector.record_scenario_complete(f"scenario_{i}", success=False)
        
        # Add some retries
        collector.record_retry("scenario_0")
        collector.record_retry("scenario_0")
        collector.record_retry("scenario_5")
        
        collector.record_run_end()
        
        stats = collector.compute_statistics("run-123", "test_eval")
        
        assert stats.execution["completed"] == 5
        assert stats.execution["failed"] == 3
        assert stats.execution["retries"] == 3
        assert len(stats.execution["retry_details"]) == 2
        
        # Verify retry details
        retry_scenarios = [r["scenario_id"] for r in stats.execution["retry_details"]]
        assert "scenario_0" in retry_scenarios
        assert "scenario_5" in retry_scenarios

    def test_metadata_iso_timestamp_format(self) -> None:
        """Timestamps are in ISO 8601 format."""
        reset_metadata_collector()
        collector = get_metadata_collector()
        
        collector.record_run_start()
        collector.record_scenario_start("scenario_1")
        collector.record_scenario_complete("scenario_1", success=True)
        collector.record_run_end()
        
        stats = collector.compute_statistics("run-123", "test_eval")
        
        # Verify ISO 8601 format (ends with Z for UTC)
        assert stats.start_time_iso.endswith("Z")
        assert stats.end_time_iso.endswith("Z")
        
        # Verify format can be parsed
        from datetime import datetime
        datetime.fromisoformat(stats.start_time_iso.replace("Z", "+00:00"))
        datetime.fromisoformat(stats.end_time_iso.replace("Z", "+00:00"))

