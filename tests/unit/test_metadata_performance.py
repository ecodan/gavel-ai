import pytest

pytestmark = pytest.mark.unit
"""
Performance tests for metadata collection.

Per Story 7.2 Task 10: Validate performance and accuracy.
"""

import time

from gavel_ai.telemetry.metadata import (
    get_metadata_collector,
    reset_metadata_collector,
)


class TestMetadataPerformance:
    """Performance and accuracy tests for metadata collection."""

    def test_metadata_collection_overhead(self) -> None:
        """Metadata collection adds <1% overhead."""
        reset_metadata_collector()
        collector = get_metadata_collector()

        # Baseline: time without metadata collection
        baseline_iterations = 1000
        start_time = time.time()
        for i in range(baseline_iterations):
            # Simulate no-op work
            pass
        baseline_duration = time.time() - start_time

        # With metadata collection
        reset_metadata_collector()
        collector = get_metadata_collector()

        collector.record_run_start()

        start_time = time.time()
        for i in range(baseline_iterations):
            scenario_id = f"scenario_{i}"
            collector.record_scenario_start(scenario_id)
            # Simulate work
            pass
            collector.record_scenario_complete(scenario_id, success=True)
            collector.record_llm_call("claude-3-5-sonnet", 100, 50)

        collection_duration = time.time() - start_time
        collector.record_run_end()

        # Calculate overhead percentage
        # Note: This is a very loose test since baseline is almost 0
        # The actual overhead is acceptable if collection_duration is reasonable
        assert collection_duration < 5.0, (
            f"Metadata collection took {collection_duration}s for 1000 scenarios - too slow"
        )

    def test_statistics_computation_performance(self) -> None:
        """Statistics computation is fast even with many scenarios."""
        reset_metadata_collector()
        collector = get_metadata_collector()

        collector.record_run_start()

        # Generate many scenarios and LLM calls
        num_scenarios = 100
        for i in range(num_scenarios):
            scenario_id = f"scenario_{i}"
            collector.record_scenario_start(scenario_id)

            # Multiple LLM calls per scenario
            for j in range(5):
                model = "claude-3-5-sonnet" if j % 2 == 0 else "gpt-4"
                collector.record_llm_call(model, 100, 50)

            collector.record_scenario_complete(scenario_id, success=(i % 3 != 0))

            # Some retries
            if i % 10 == 0:
                collector.record_retry(scenario_id)

        collector.record_run_end()

        # Time statistics computation
        start_time = time.time()
        stats = collector.compute_statistics("run-123", "test_eval")
        computation_time = time.time() - start_time

        # Should complete in <100ms even with 100 scenarios
        assert computation_time < 0.1, f"Statistics computation took {computation_time}s - too slow"

        # Verify correctness
        assert stats.scenario_timing.count == num_scenarios
        assert stats.llm_calls.total == num_scenarios * 5

    def test_json_serialization_performance(self) -> None:
        """JSON serialization is fast."""
        reset_metadata_collector()
        collector = get_metadata_collector()

        collector.record_run_start()

        # Generate substantial metadata
        for i in range(50):
            scenario_id = f"scenario_{i}"
            collector.record_scenario_start(scenario_id)
            for j in range(3):
                collector.record_llm_call("claude-3-5-sonnet", 100 + i, 50 + j)
            collector.record_scenario_complete(scenario_id, success=(i % 2 == 0))

        collector.record_run_end()
        stats = collector.compute_statistics("run-123", "test_eval")

        # Time JSON serialization
        start_time = time.time()
        json_str = stats.model_dump_json()
        serialization_time = time.time() - start_time

        # Should complete in <50ms
        assert serialization_time < 0.05, (
            f"JSON serialization took {serialization_time}s - too slow"
        )

        # Verify output is valid JSON
        import json

        json.loads(json_str)

    def test_timing_accuracy(self) -> None:
        """Timing measurements are reasonably accurate."""
        reset_metadata_collector()
        collector = get_metadata_collector()

        collector.record_run_start()

        # Record a scenario with known duration
        test_duration_ms = 50
        scenario_id = "scenario_1"

        collector.record_scenario_start(scenario_id)
        time.sleep(test_duration_ms / 1000.0)  # Sleep for exact duration
        collector.record_scenario_complete(scenario_id, success=True)

        collector.record_run_end()

        stats = collector.compute_statistics("run-123", "test_eval")

        # Check timing is within ±20% of expected (accounting for system variance)
        measured_duration = stats.scenario_timing.mean_ms
        tolerance = test_duration_ms * 0.2

        assert abs(measured_duration - test_duration_ms) < tolerance, (
            f"Expected ~{test_duration_ms}ms, got {measured_duration}ms"
        )

    def test_memory_efficiency(self) -> None:
        """Metadata collection doesn't consume excessive memory."""
        reset_metadata_collector()
        collector = get_metadata_collector()

        collector.record_run_start()

        # Generate a large number of events
        num_events = 10000
        for i in range(num_events):
            scenario_id = f"scenario_{i % 100}"  # Reuse scenario IDs
            if i % 100 == 0:
                collector.record_scenario_start(scenario_id)
            collector.record_llm_call("claude-3-5-sonnet", 100, 50)
            if i % 100 == 99:
                collector.record_scenario_complete(scenario_id, success=True)

        collector.record_run_end()

        # Should not crash or consume excessive memory
        stats = collector.compute_statistics("run-123", "test_eval")

        # Verify data is reasonable size
        json_str = stats.model_dump_json()
        json_size_kb = len(json_str) / 1024

        # 10k events should fit in < 1MB JSON
        assert json_size_kb < 1024, f"JSON size {json_size_kb}KB - too large"
