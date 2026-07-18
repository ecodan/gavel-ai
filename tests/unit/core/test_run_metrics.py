"""Unit tests for run performance metrics computation (real OutputRecord instances)."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import pytest

from gavel_ai.core.exceptions import ValidationError
from gavel_ai.core.run_metrics import compute_run_metrics
from gavel_ai.models.runtime import OutputRecord

pytestmark = pytest.mark.unit


def _record(
    scenario_id: str,
    timing_ms: int = 100,
    error: str | None = None,
    tokens_prompt: int = 10,
    tokens_completion: int = 5,
    timestamp: str | None = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> OutputRecord:
    return OutputRecord(
        test_subject="test-subject",
        variant_id="v1",
        scenario_id=scenario_id,
        processor_output="output",
        timing_ms=timing_ms,
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
        error=error,
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
        metadata=metadata or {},
    )


class TestComputeRunMetrics:
    def test_empty_records_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError, match="empty"):
            compute_run_metrics([])

    def test_counts_success_and_error(self) -> None:
        records = [
            _record("1"),
            _record("2", error="boom"),
            _record("3"),
        ]
        metrics = compute_run_metrics(records)
        assert metrics.scenario_count == 3
        assert metrics.success_count == 2
        assert metrics.warning_count == 0
        assert metrics.error_count == 1
        assert metrics.error_rate == pytest.approx(1 / 3)

    def test_warning_tier_counted_separately_from_error(self) -> None:
        """PROCESS_SUCCESS_WITH_ISSUE (WARNING tier) is not a hard failure and
        must not inflate error_rate the same way a real PROCESS_FAILURE does."""
        records = [
            _record("1"),
            _record(
                "2",
                error="External system issue [warning] soft_issue: recoverable",
                metadata={"external_tier": "WARNING"},
            ),
            _record(
                "3",
                error="External script process failure: crash",
                metadata={"external_tier": "ERROR"},
            ),
        ]
        metrics = compute_run_metrics(records)
        assert metrics.scenario_count == 3
        assert metrics.success_count == 1
        assert metrics.warning_count == 1
        assert metrics.error_count == 1
        assert metrics.error_rate == pytest.approx(1 / 3)

    def test_latency_stats(self) -> None:
        records = [_record(str(i), timing_ms=timing) for i, timing in enumerate([100, 200, 300, 400])]
        metrics = compute_run_metrics(records)
        assert metrics.latency_avg_ms == pytest.approx(250.0)
        assert metrics.latency_p50_ms is not None
        assert metrics.latency_p95_ms is not None
        assert metrics.latency_p50_ms <= metrics.latency_p95_ms

    def test_single_record_latency(self) -> None:
        metrics = compute_run_metrics([_record("1", timing_ms=150)])
        assert metrics.latency_avg_ms == 150
        assert metrics.latency_p50_ms == 150
        assert metrics.latency_p95_ms == 150

    def test_token_totals(self) -> None:
        records = [
            _record("1", tokens_prompt=10, tokens_completion=5),
            _record("2", tokens_prompt=20, tokens_completion=15),
        ]
        metrics = compute_run_metrics(records)
        assert metrics.tokens_prompt_total == 30
        assert metrics.tokens_completion_total == 20

    def test_throughput_computed_from_reconstructed_execution_window(self) -> None:
        """timing_ms=0 isolates pure completion-timestamp spread as the window."""
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        records = [
            _record("1", timing_ms=0, timestamp=(base + timedelta(seconds=0)).isoformat()),
            _record("2", timing_ms=0, timestamp=(base + timedelta(seconds=1)).isoformat()),
            _record("3", timing_ms=0, timestamp=(base + timedelta(seconds=2)).isoformat()),
        ]
        metrics = compute_run_metrics(records)
        assert metrics.throughput_per_sec == pytest.approx(1.5, rel=0.01)

    def test_throughput_reflects_concurrent_execution_not_write_time_clustering(self) -> None:
        """Regression test: concurrent scenarios complete (and get spooled to disk)
        within milliseconds of each other, but each took real wall-clock time to
        run. Throughput must reflect that real duration, not the near-zero spread
        of completion timestamps."""
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        records = [
            _record(
                str(i),
                timing_ms=5000,
                timestamp=(base + timedelta(milliseconds=i)).isoformat(),
            )
            for i in range(5)
        ]
        metrics = compute_run_metrics(records)
        # 5 records each taking ~5s, running concurrently -> window ~= 5s, not ~4ms.
        assert metrics.throughput_per_sec == pytest.approx(1.0, rel=0.05)

    def test_throughput_none_when_all_timestamps_identical(self) -> None:
        same_ts = datetime.now(timezone.utc).isoformat()
        records = [
            _record("1", timing_ms=0, timestamp=same_ts),
            _record("2", timing_ms=0, timestamp=same_ts),
        ]
        metrics = compute_run_metrics(records)
        assert metrics.throughput_per_sec is None

    def test_throughput_none_with_single_record(self) -> None:
        metrics = compute_run_metrics([_record("1")])
        assert metrics.throughput_per_sec is None

    def test_malformed_timestamp_is_tolerated(self) -> None:
        records = [_record("1", timestamp="not-a-timestamp"), _record("2", timestamp="also-bad")]
        metrics = compute_run_metrics(records)
        assert metrics.throughput_per_sec is None
        assert metrics.scenario_count == 2
