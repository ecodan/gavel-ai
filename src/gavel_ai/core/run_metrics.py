"""
Performance-metrics computation over ``results_raw.jsonl`` (OutputRecord list).

Transport-agnostic: works identically for prompt-based and external
(script/http) system-under-test runs, since both populate the same
``OutputRecord`` fields (``timing_ms``, ``tokens_prompt``, ``tokens_completion``,
``error``, ``timestamp``).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from gavel_ai.core.exceptions import ValidationError
from gavel_ai.models.runtime import OutputRecord


@dataclass(frozen=True)
class RunMetrics:
    """Aggregate performance metrics for a single run."""

    scenario_count: int
    success_count: int
    warning_count: int
    error_count: int
    error_rate: float
    latency_avg_ms: Optional[float]
    latency_p50_ms: Optional[float]
    latency_p95_ms: Optional[float]
    throughput_per_sec: Optional[float]
    tokens_prompt_total: int
    tokens_completion_total: int


def _percentile(sorted_values: List[float], pct: float) -> float:
    """Nearest-rank percentile over an already-sorted list. ``pct`` in [0, 100]."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = pct / 100 * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    frac = rank - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * frac


def compute_run_metrics(records: List[OutputRecord]) -> RunMetrics:
    """Compute aggregate performance metrics from raw processor output records.

    Args:
        records: Records loaded from results_raw.jsonl.

    Returns:
        RunMetrics with counts, latency percentiles, throughput, and token totals.

    Raises:
        ValidationError: If ``records`` is empty.
    """
    if not records:
        raise ValidationError("Cannot compute metrics for an empty result set")

    scenario_count = len(records)
    warning_count = sum(
        1 for r in records if r.error and r.metadata.get("external_tier") == "WARNING"
    )
    error_count = sum(
        1 for r in records if r.error and r.metadata.get("external_tier") != "WARNING"
    )
    success_count = scenario_count - error_count - warning_count
    error_rate = error_count / scenario_count

    latencies = sorted(r.timing_ms for r in records if r.timing_ms is not None)
    latency_avg_ms = sum(latencies) / len(latencies) if latencies else None
    latency_p50_ms = _percentile(latencies, 50) if latencies else None
    latency_p95_ms = _percentile(latencies, 95) if latencies else None

    throughput_per_sec = _compute_throughput(records)

    tokens_prompt_total = sum(r.tokens_prompt for r in records)
    tokens_completion_total = sum(r.tokens_completion for r in records)

    return RunMetrics(
        scenario_count=scenario_count,
        success_count=success_count,
        warning_count=warning_count,
        error_count=error_count,
        error_rate=error_rate,
        latency_avg_ms=latency_avg_ms,
        latency_p50_ms=latency_p50_ms,
        latency_p95_ms=latency_p95_ms,
        throughput_per_sec=throughput_per_sec,
        tokens_prompt_total=tokens_prompt_total,
        tokens_completion_total=tokens_completion_total,
    )


def _compute_throughput(records: List[OutputRecord]) -> Optional[float]:
    """Records per second across the observed execution window, or None if unavailable.

    Records execute concurrently and are spooled to results_raw.jsonl within
    milliseconds of each other once the whole batch finishes, so the spread of
    ``timestamp`` values alone is not a usable proxy for wall-clock duration —
    it reflects write-time clustering, not execution time. Each record's own
    ``timing_ms`` is used to reconstruct that scenario's start time (completion
    ``timestamp`` minus its duration), and the window from the earliest
    reconstructed start to the latest completion approximates the batch's real
    wall-clock span under concurrent execution.
    """
    windows: List[tuple[datetime, datetime]] = []
    for r in records:
        try:
            end = datetime.fromisoformat(r.timestamp)
        except (ValueError, TypeError):
            continue
        start = end - timedelta(milliseconds=r.timing_ms)
        windows.append((start, end))

    if len(windows) < 2:
        return None

    window_start = min(start for start, _ in windows)
    window_end = max(end for _, end in windows)
    span_sec = (window_end - window_start).total_seconds()
    if span_sec <= 0:
        return None

    return len(windows) / span_sec
