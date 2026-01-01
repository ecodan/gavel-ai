"""
Run metadata collection and schema for per-run metrics.

Per Story 7.2: Captures timing, token counts, and execution statistics during evaluation runs.

This module provides:
- RunMetadataSchema: Pydantic model for run_metadata.json structure
- RunMetadataCollector: Collects timing and token data during execution
- Helper models: ScenarioTimingStats, LLMMetrics for structured data
"""

from datetime import datetime, timezone
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ScenarioTimingStats(BaseModel):
    """Statistics for scenario execution timing."""

    count: int = Field(..., ge=0, description="Number of scenarios processed")
    mean_ms: float = Field(..., ge=0, description="Mean scenario duration in milliseconds")
    median_ms: float = Field(..., ge=0, description="Median scenario duration in milliseconds")
    min_ms: float = Field(..., ge=0, description="Minimum scenario duration in milliseconds")
    max_ms: float = Field(..., ge=0, description="Maximum scenario duration in milliseconds")
    std_ms: float = Field(..., ge=0, description="Standard deviation of scenario duration in milliseconds")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "count": 10,
                "mean_ms": 2500.0,
                "median_ms": 2400.0,
                "min_ms": 1800.0,
                "max_ms": 3200.0,
                "std_ms": 450.0,
            }
        }
    )


class LLMMetrics(BaseModel):
    """Aggregated LLM call metrics."""

    total: int = Field(..., ge=0, description="Total number of LLM calls")
    by_model: Dict[str, int] = Field(
        ..., description="Count of calls per model name"
    )
    tokens: Dict[str, Any] = Field(
        ...,
        description="Token counts with structure: {prompt_total, completion_total, by_model: {model_name: {prompt, completion}}}",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 40,
                "by_model": {
                    "claude-3-5-sonnet": 20,
                    "gpt-4": 20,
                },
                "tokens": {
                    "prompt_total": 5000,
                    "completion_total": 2000,
                    "by_model": {
                        "claude-3-5-sonnet": {
                            "prompt": 2500,
                            "completion": 1000,
                        },
                        "gpt-4": {
                            "prompt": 2500,
                            "completion": 1000,
                        },
                    },
                },
            }
        }
    )


class RunMetadataSchema(BaseModel):
    """Complete run metadata schema matching specification in Story 7.2."""

    run_id: str = Field(..., description="Run identifier")
    eval_name: str = Field(..., description="Evaluation name")
    start_time_iso: str = Field(..., description="Run start time in ISO 8601 format")
    end_time_iso: str = Field(..., description="Run end time in ISO 8601 format")
    total_duration_seconds: float = Field(
        ..., ge=0, description="Total run duration in seconds"
    )
    scenario_timing: ScenarioTimingStats = Field(
        ..., description="Scenario timing statistics"
    )
    llm_calls: LLMMetrics = Field(..., description="LLM call metrics")
    execution: Dict[str, Any] = Field(
        ...,
        description="Execution summary with: completed, failed, retries, retry_details",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "run-20251231-120000",
                "eval_name": "test_os",
                "start_time_iso": "2025-12-31T12:00:00Z",
                "end_time_iso": "2025-12-31T12:02:00Z",
                "total_duration_seconds": 120,
                "scenario_timing": {
                    "count": 10,
                    "mean_ms": 2500.0,
                    "median_ms": 2400.0,
                    "min_ms": 1800.0,
                    "max_ms": 3200.0,
                    "std_ms": 450.0,
                },
                "llm_calls": {
                    "total": 40,
                    "by_model": {"claude-3-5-sonnet": 20},
                    "tokens": {
                        "prompt_total": 5000,
                        "completion_total": 2000,
                        "by_model": {
                            "claude-3-5-sonnet": {
                                "prompt": 2500,
                                "completion": 1000,
                            }
                        },
                    },
                },
                "execution": {
                    "completed": 10,
                    "failed": 0,
                    "retries": 2,
                    "retry_details": [],
                },
            }
        }
    )


class RunMetadataCollector:
    """Collects runtime metrics during evaluation execution."""

    def __init__(self) -> None:
        """Initialize collector with empty data structures."""
        self.scenario_timings: Dict[str, Dict[str, float]] = {}  # scenario_id -> {start, end}
        self.llm_calls: List[Dict[str, Any]] = []  # List of {model, prompt_tokens, completion_tokens}
        self.retries: Dict[str, int] = {}  # scenario_id -> count
        self.scenario_success: Dict[str, bool] = {}  # scenario_id -> success status
        self.run_start_time: Optional[float] = None
        self.run_end_time: Optional[float] = None

    def record_run_start(self) -> None:
        """Record run start time."""
        import time

        self.run_start_time = time.time()

    def record_run_end(self) -> None:
        """Record run end time."""
        import time

        self.run_end_time = time.time()

    def record_scenario_start(self, scenario_id: str) -> None:
        """Record scenario start time.

        Args:
            scenario_id: ID of scenario starting
        """
        import time

        if scenario_id not in self.scenario_timings:
            self.scenario_timings[scenario_id] = {}
        self.scenario_timings[scenario_id]["start"] = time.time()

    def record_scenario_complete(self, scenario_id: str, success: bool) -> None:
        """Record scenario completion time and success status.

        Args:
            scenario_id: ID of scenario completing
            success: Whether scenario completed successfully
        """
        import time

        if scenario_id not in self.scenario_timings:
            self.scenario_timings[scenario_id] = {}
        self.scenario_timings[scenario_id]["end"] = time.time()
        self.scenario_success[scenario_id] = success

    def record_llm_call(
        self, model: str, prompt_tokens: int, completion_tokens: int
    ) -> None:
        """Record an LLM call with token counts.

        Args:
            model: LLM model name (e.g., "claude-3-5-sonnet")
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens generated
        """
        self.llm_calls.append(
            {
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        )

    def record_retry(self, scenario_id: str) -> None:
        """Record a retry attempt for a scenario.

        Args:
            scenario_id: ID of scenario being retried
        """
        if scenario_id not in self.retries:
            self.retries[scenario_id] = 0
        self.retries[scenario_id] += 1

    def compute_statistics(
        self,
        run_id: str,
        eval_name: str,
    ) -> RunMetadataSchema:
        """Compute aggregated statistics and generate RunMetadataSchema.

        Args:
            run_id: Run identifier
            eval_name: Evaluation name

        Returns:
            RunMetadataSchema instance with all computed statistics
        """
        # Compute scenario timing statistics
        scenario_durations_ms: List[float] = []
        for scenario_id, timings in self.scenario_timings.items():
            if "start" in timings and "end" in timings:
                duration_ms = (timings["end"] - timings["start"]) * 1000
                scenario_durations_ms.append(duration_ms)

        scenario_count = len(scenario_durations_ms)
        if scenario_count > 0:
            scenario_mean_ms = mean(scenario_durations_ms)
            scenario_median_ms = median(scenario_durations_ms)
            scenario_min_ms = min(scenario_durations_ms)
            scenario_max_ms = max(scenario_durations_ms)
            scenario_std_ms = stdev(scenario_durations_ms) if scenario_count > 1 else 0.0
        else:
            scenario_mean_ms = 0.0
            scenario_median_ms = 0.0
            scenario_min_ms = 0.0
            scenario_max_ms = 0.0
            scenario_std_ms = 0.0

        scenario_timing = ScenarioTimingStats(
            count=scenario_count,
            mean_ms=scenario_mean_ms,
            median_ms=scenario_median_ms,
            min_ms=scenario_min_ms,
            max_ms=scenario_max_ms,
            std_ms=scenario_std_ms,
        )

        # Compute LLM metrics
        llm_by_model: Dict[str, int] = {}
        llm_tokens_by_model: Dict[str, Dict[str, int]] = {}
        total_prompt_tokens = 0
        total_completion_tokens = 0

        for call in self.llm_calls:
            model = call["model"]
            prompt_tokens = call["prompt_tokens"]
            completion_tokens = call["completion_tokens"]

            llm_by_model[model] = llm_by_model.get(model, 0) + 1
            total_prompt_tokens += prompt_tokens
            total_completion_tokens += completion_tokens

            if model not in llm_tokens_by_model:
                llm_tokens_by_model[model] = {"prompt": 0, "completion": 0}
            llm_tokens_by_model[model]["prompt"] += prompt_tokens
            llm_tokens_by_model[model]["completion"] += completion_tokens

        llm_calls = LLMMetrics(
            total=len(self.llm_calls),
            by_model=llm_by_model,
            tokens={
                "prompt_total": total_prompt_tokens,
                "completion_total": total_completion_tokens,
                "by_model": llm_tokens_by_model,
            },
        )

        # Compute execution summary
        completed_count = sum(
            1 for success in self.scenario_success.values() if success
        )
        failed_count = sum(
            1 for success in self.scenario_success.values() if not success
        )
        total_retries = sum(self.retries.values())
        retry_details = [
            {"scenario_id": scenario_id, "retry_count": count}
            for scenario_id, count in self.retries.items()
            if count > 0
        ]

        execution = {
            "completed": completed_count,
            "failed": failed_count,
            "retries": total_retries,
            "retry_details": retry_details,
        }

        # Compute total duration
        if self.run_start_time and self.run_end_time:
            total_duration_seconds = self.run_end_time - self.run_start_time
        else:
            total_duration_seconds = 0.0

        # Format timestamps
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        start_time_iso = now_iso
        end_time_iso = now_iso

        return RunMetadataSchema(
            run_id=run_id,
            eval_name=eval_name,
            start_time_iso=start_time_iso,
            end_time_iso=end_time_iso,
            total_duration_seconds=total_duration_seconds,
            scenario_timing=scenario_timing,
            llm_calls=llm_calls,
            execution=execution,
        )

    def reset(self) -> None:
        """Reset collector to initial state."""
        self.scenario_timings = {}
        self.llm_calls = []
        self.retries = {}
        self.scenario_success = {}
        self.run_start_time = None
        self.run_end_time = None


# Global metadata collector instance
_metadata_collector: Optional[RunMetadataCollector] = None


def get_metadata_collector() -> RunMetadataCollector:
    """
    Get the current metadata collector instance.

    Creates a new collector if one doesn't exist yet.

    Returns:
        RunMetadataCollector instance
    """
    global _metadata_collector

    if _metadata_collector is None:
        _metadata_collector = RunMetadataCollector()

    return _metadata_collector


def reset_metadata_collector() -> None:
    """
    Reset the metadata collector after a run completes.

    This should be called after metrics have been exported.
    """
    global _metadata_collector

    if _metadata_collector is not None:
        _metadata_collector.reset()
        _metadata_collector = None


__all__ = [
    "ScenarioTimingStats",
    "LLMMetrics",
    "RunMetadataSchema",
    "RunMetadataCollector",
    "get_metadata_collector",
    "reset_metadata_collector",
]
