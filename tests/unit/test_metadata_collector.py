import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for RunMetadataCollector.

Per Story 7.2 Task 9: Comprehensive tests for metadata collection.
"""

import time

from gavel_ai.telemetry.metadata import RunMetadataCollector, RunMetadataSchema


class TestRunMetadataCollector:
    """Tests for RunMetadataCollector class."""

    def test_collector_initialization(self) -> None:
        """Collector initializes with empty data structures."""
        collector = RunMetadataCollector()

        assert collector.scenario_timings == {}
        assert collector.llm_calls == []
        assert collector.retries == {}
        assert collector.scenario_success == {}
        assert collector.run_start_time is None
        assert collector.run_end_time is None

    def test_record_scenario_start(self) -> None:
        """record_scenario_start records start time."""
        collector = RunMetadataCollector()
        scenario_id = "scenario_1"

        collector.record_scenario_start(scenario_id)

        assert scenario_id in collector.scenario_timings
        assert "start" in collector.scenario_timings[scenario_id]
        assert collector.scenario_timings[scenario_id]["start"] > 0

    def test_record_scenario_complete(self) -> None:
        """record_scenario_complete records end time and success."""
        collector = RunMetadataCollector()
        scenario_id = "scenario_1"

        collector.record_scenario_start(scenario_id)
        time.sleep(0.01)  # Small delay to ensure time difference
        collector.record_scenario_complete(scenario_id, success=True)

        assert scenario_id in collector.scenario_timings
        assert "end" in collector.scenario_timings[scenario_id]
        assert collector.scenario_success[scenario_id] is True
        # Verify end time is after start time
        assert (
            collector.scenario_timings[scenario_id]["end"]
            > collector.scenario_timings[scenario_id]["start"]
        )

    def test_record_scenario_failure(self) -> None:
        """record_scenario_complete records failure status."""
        collector = RunMetadataCollector()
        scenario_id = "scenario_1"

        collector.record_scenario_start(scenario_id)
        collector.record_scenario_complete(scenario_id, success=False)

        assert collector.scenario_success[scenario_id] is False

    def test_record_llm_call(self) -> None:
        """record_llm_call records model and token counts."""
        collector = RunMetadataCollector()

        collector.record_llm_call("claude-3-5-sonnet", 100, 50)

        assert len(collector.llm_calls) == 1
        assert collector.llm_calls[0]["model"] == "claude-3-5-sonnet"
        assert collector.llm_calls[0]["prompt_tokens"] == 100
        assert collector.llm_calls[0]["completion_tokens"] == 50

    def test_record_multiple_llm_calls(self) -> None:
        """Multiple LLM calls are recorded."""
        collector = RunMetadataCollector()

        collector.record_llm_call("claude-3-5-sonnet", 100, 50)
        collector.record_llm_call("gpt-4", 200, 100)
        collector.record_llm_call("claude-3-5-sonnet", 150, 75)

        assert len(collector.llm_calls) == 3
        # Verify all calls recorded
        models = [call["model"] for call in collector.llm_calls]
        assert models.count("claude-3-5-sonnet") == 2
        assert models.count("gpt-4") == 1

    def test_record_retry(self) -> None:
        """record_retry increments retry count."""
        collector = RunMetadataCollector()
        scenario_id = "scenario_1"

        assert scenario_id not in collector.retries

        collector.record_retry(scenario_id)
        assert collector.retries[scenario_id] == 1

        collector.record_retry(scenario_id)
        assert collector.retries[scenario_id] == 2

    def test_record_run_start_and_end(self) -> None:
        """record_run_start and record_run_end track run timing."""
        collector = RunMetadataCollector()

        collector.record_run_start()
        assert collector.run_start_time is not None

        time.sleep(0.01)
        collector.record_run_end()
        assert collector.run_end_time is not None
        assert collector.run_end_time > collector.run_start_time

    def test_compute_statistics_no_scenarios(self) -> None:
        """compute_statistics handles empty collector."""
        collector = RunMetadataCollector()
        collector.record_run_start()
        collector.record_run_end()

        stats = collector.compute_statistics("run-123", "test_eval")

        assert isinstance(stats, RunMetadataSchema)
        assert stats.run_id == "run-123"
        assert stats.eval_name == "test_eval"
        assert stats.scenario_timing.count == 0
        assert stats.scenario_timing.mean_ms == 0.0
        assert stats.llm_calls.total == 0

    def test_compute_statistics_single_scenario(self) -> None:
        """compute_statistics with single scenario."""
        collector = RunMetadataCollector()
        collector.record_run_start()

        # Record one scenario
        collector.record_scenario_start("scenario_1")
        time.sleep(0.01)
        collector.record_scenario_complete("scenario_1", success=True)

        collector.record_run_end()

        stats = collector.compute_statistics("run-123", "test_eval")

        assert stats.scenario_timing.count == 1
        assert stats.scenario_timing.mean_ms > 0
        assert stats.scenario_timing.min_ms > 0
        assert stats.scenario_timing.max_ms > 0
        assert stats.scenario_timing.median_ms > 0
        # Single scenario: std dev should be 0
        assert stats.scenario_timing.std_ms == 0.0

    def test_compute_statistics_multiple_scenarios(self) -> None:
        """compute_statistics with multiple scenarios."""
        collector = RunMetadataCollector()
        collector.record_run_start()

        # Record three scenarios
        for i in range(3):
            scenario_id = f"scenario_{i}"
            collector.record_scenario_start(scenario_id)
            time.sleep(0.01)
            collector.record_scenario_complete(scenario_id, success=(i % 2 == 0))

        collector.record_run_end()

        stats = collector.compute_statistics("run-123", "test_eval")

        assert stats.scenario_timing.count == 3
        assert stats.scenario_timing.mean_ms > 0
        assert stats.scenario_timing.std_ms > 0
        assert stats.execution["completed"] == 2  # scenarios 0 and 2
        assert stats.execution["failed"] == 1  # scenario 1

    def test_compute_statistics_with_llm_calls(self) -> None:
        """compute_statistics aggregates LLM calls by model."""
        collector = RunMetadataCollector()
        collector.record_run_start()

        collector.record_scenario_start("scenario_1")
        collector.record_llm_call("claude-3-5-sonnet", 100, 50)
        collector.record_llm_call("gpt-4", 200, 100)
        collector.record_llm_call("claude-3-5-sonnet", 150, 75)
        collector.record_scenario_complete("scenario_1", success=True)

        collector.record_run_end()

        stats = collector.compute_statistics("run-123", "test_eval")

        assert stats.llm_calls.total == 3
        assert stats.llm_calls.by_model["claude-3-5-sonnet"] == 2
        assert stats.llm_calls.by_model["gpt-4"] == 1
        assert stats.llm_calls.tokens["prompt_total"] == 450  # 100 + 200 + 150
        assert stats.llm_calls.tokens["completion_total"] == 225  # 50 + 100 + 75

        # Per-model token counts
        assert stats.llm_calls.tokens["by_model"]["claude-3-5-sonnet"]["prompt"] == 250
        assert stats.llm_calls.tokens["by_model"]["claude-3-5-sonnet"]["completion"] == 125
        assert stats.llm_calls.tokens["by_model"]["gpt-4"]["prompt"] == 200
        assert stats.llm_calls.tokens["by_model"]["gpt-4"]["completion"] == 100

    def test_compute_statistics_with_retries(self) -> None:
        """compute_statistics tracks retry counts."""
        collector = RunMetadataCollector()
        collector.record_run_start()

        collector.record_scenario_start("scenario_1")
        collector.record_scenario_complete("scenario_1", success=True)
        collector.record_retry("scenario_1")
        collector.record_retry("scenario_1")

        collector.record_scenario_start("scenario_2")
        collector.record_scenario_complete("scenario_2", success=False)
        # No retries for scenario_2

        collector.record_run_end()

        stats = collector.compute_statistics("run-123", "test_eval")

        assert stats.execution["retries"] == 2
        assert len(stats.execution["retry_details"]) == 1
        assert stats.execution["retry_details"][0]["scenario_id"] == "scenario_1"
        assert stats.execution["retry_details"][0]["retry_count"] == 2

    def test_reset_collector(self) -> None:
        """reset() clears all collected data."""
        collector = RunMetadataCollector()

        # Record some data
        collector.record_run_start()
        collector.record_scenario_start("scenario_1")
        collector.record_scenario_complete("scenario_1", success=True)
        collector.record_llm_call("claude-3-5-sonnet", 100, 50)
        collector.record_retry("scenario_1")

        # Verify data is present
        assert len(collector.scenario_timings) > 0
        assert len(collector.llm_calls) > 0
        assert len(collector.retries) > 0

        # Reset
        collector.reset()

        # Verify all data is cleared
        assert collector.scenario_timings == {}
        assert collector.llm_calls == []
        assert collector.retries == {}
        assert collector.scenario_success == {}
        assert collector.run_start_time is None
        assert collector.run_end_time is None

    def test_scenario_timing_calculations(self) -> None:
        """Timing statistics are calculated correctly."""
        collector = RunMetadataCollector()
        collector.record_run_start()

        # Record scenarios with controlled timing
        durations_ms = []
        for i in range(3):
            scenario_id = f"scenario_{i}"
            collector.record_scenario_start(scenario_id)
            # Simulate different durations
            delay = 0.01 * (i + 1)
            time.sleep(delay)
            collector.record_scenario_complete(scenario_id, success=True)

            duration_ms = (
                collector.scenario_timings[scenario_id]["end"]
                - collector.scenario_timings[scenario_id]["start"]
            ) * 1000
            durations_ms.append(duration_ms)

        collector.record_run_end()

        stats = collector.compute_statistics("run-123", "test_eval")

        # Verify statistics are consistent with actual durations
        assert stats.scenario_timing.count == 3
        assert stats.scenario_timing.min_ms == min(durations_ms)
        assert stats.scenario_timing.max_ms == max(durations_ms)
        # Mean should be close to average of durations (within 1ms)
        expected_mean = sum(durations_ms) / len(durations_ms)
        assert abs(stats.scenario_timing.mean_ms - expected_mean) < 1.0
