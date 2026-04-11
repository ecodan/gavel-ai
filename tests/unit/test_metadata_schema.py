import pytest

pytestmark = pytest.mark.unit
"""
Unit tests for run_metadata.json schema and Pydantic models.

Per Story 7.2 Task 1: Schema validation, JSON serialization, invalid data rejection.
"""

import json
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from gavel_ai.telemetry.metadata import (
    LLMMetrics,
    RunMetadataSchema,
    ScenarioTimingStats,
)


class TestScenarioTimingStats:
    """Tests for ScenarioTimingStats model."""

    def test_valid_scenario_timing_stats(self) -> None:
        """Valid timing stats are accepted."""
        stats = ScenarioTimingStats(
            count=10,
            mean_ms=2500.0,
            median_ms=2400.0,
            min_ms=1800.0,
            max_ms=3200.0,
            std_ms=450.0,
        )
        assert stats.count == 10
        assert stats.mean_ms == 2500.0

    def test_negative_timing_values_rejected(self) -> None:
        """Negative timing values are rejected."""
        with pytest.raises(ValidationError):
            ScenarioTimingStats(
                count=10,
                mean_ms=-2500.0,  # Invalid: negative
                median_ms=2400.0,
                min_ms=1800.0,
                max_ms=3200.0,
                std_ms=450.0,
            )

    def test_zero_count_valid(self) -> None:
        """Zero count is valid (no scenarios completed)."""
        stats = ScenarioTimingStats(
            count=0,
            mean_ms=0.0,
            median_ms=0.0,
            min_ms=0.0,
            max_ms=0.0,
            std_ms=0.0,
        )
        assert stats.count == 0

    def test_json_serialization(self) -> None:
        """ScenarioTimingStats serializes to JSON."""
        stats = ScenarioTimingStats(
            count=10,
            mean_ms=2500.0,
            median_ms=2400.0,
            min_ms=1800.0,
            max_ms=3200.0,
            std_ms=450.0,
        )
        json_str = stats.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["count"] == 10
        assert parsed["mean_ms"] == 2500.0


class TestLLMMetrics:
    """Tests for LLMMetrics model."""

    def test_valid_llm_metrics(self) -> None:
        """Valid LLM metrics are accepted."""
        metrics = LLMMetrics(
            total=40,
            by_model={"claude-3-5-sonnet": 20, "gpt-4": 20},
            tokens={
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
        )
        assert metrics.total == 40
        assert metrics.by_model["claude-3-5-sonnet"] == 20

    def test_empty_llm_metrics(self) -> None:
        """Empty LLM metrics (no calls) are valid."""
        metrics = LLMMetrics(
            total=0,
            by_model={},
            tokens={
                "prompt_total": 0,
                "completion_total": 0,
                "by_model": {},
            },
        )
        assert metrics.total == 0

    def test_json_serialization(self) -> None:
        """LLMMetrics serializes to JSON."""
        metrics = LLMMetrics(
            total=40,
            by_model={"claude-3-5-sonnet": 20},
            tokens={
                "prompt_total": 2500,
                "completion_total": 1000,
                "by_model": {
                    "claude-3-5-sonnet": {
                        "prompt": 2500,
                        "completion": 1000,
                    }
                },
            },
        )
        json_str = metrics.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["total"] == 40


class TestRunMetadataSchema:
    """Tests for RunMetadataSchema model."""

    def test_valid_run_metadata(self) -> None:
        """Valid run metadata is accepted."""
        now = datetime.now(timezone.utc)
        metadata = RunMetadataSchema(
            run_id="run-20251231-120000",
            eval_name="test_os",
            start_time_iso=now.isoformat() + "Z",
            end_time_iso=now.isoformat() + "Z",
            total_duration_seconds=120,
            scenario_timing=ScenarioTimingStats(
                count=10,
                mean_ms=2500.0,
                median_ms=2400.0,
                min_ms=1800.0,
                max_ms=3200.0,
                std_ms=450.0,
            ),
            llm_calls=LLMMetrics(
                total=40,
                by_model={"claude-3-5-sonnet": 20},
                tokens={
                    "prompt_total": 5000,
                    "completion_total": 2000,
                    "by_model": {
                        "claude-3-5-sonnet": {
                            "prompt": 2500,
                            "completion": 1000,
                        }
                    },
                },
            ),
            execution={
                "completed": 10,
                "failed": 0,
                "retries": 2,
                "retry_details": [],
            },
        )
        assert metadata.run_id == "run-20251231-120000"
        assert metadata.eval_name == "test_os"
        assert metadata.total_duration_seconds == 120

    def test_missing_required_fields_rejected(self) -> None:
        """Missing required fields are rejected."""
        with pytest.raises(ValidationError):
            RunMetadataSchema(
                run_id="run-123",
                # Missing eval_name, start_time_iso, etc.
            )

    def test_json_serialization_roundtrip(self) -> None:
        """RunMetadataSchema serializes to JSON and back."""
        now = datetime.now(timezone.utc)
        original = RunMetadataSchema(
            run_id="run-20251231-120000",
            eval_name="test_os",
            start_time_iso=now.isoformat() + "Z",
            end_time_iso=now.isoformat() + "Z",
            total_duration_seconds=120,
            scenario_timing=ScenarioTimingStats(
                count=10,
                mean_ms=2500.0,
                median_ms=2400.0,
                min_ms=1800.0,
                max_ms=3200.0,
                std_ms=450.0,
            ),
            llm_calls=LLMMetrics(
                total=40,
                by_model={"claude-3-5-sonnet": 20},
                tokens={
                    "prompt_total": 5000,
                    "completion_total": 2000,
                    "by_model": {
                        "claude-3-5-sonnet": {
                            "prompt": 2500,
                            "completion": 1000,
                        }
                    },
                },
            ),
            execution={
                "completed": 10,
                "failed": 0,
                "retries": 2,
                "retry_details": [],
            },
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Deserialize back
        parsed_dict = json.loads(json_str)
        restored = RunMetadataSchema(**parsed_dict)

        # Verify fields match
        assert restored.run_id == original.run_id
        assert restored.eval_name == original.eval_name
        assert restored.total_duration_seconds == original.total_duration_seconds

    def test_invalid_duration_rejected(self) -> None:
        """Negative duration is rejected."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            RunMetadataSchema(
                run_id="run-123",
                eval_name="test",
                start_time_iso=now.isoformat() + "Z",
                end_time_iso=now.isoformat() + "Z",
                total_duration_seconds=-1,  # Invalid
                scenario_timing=ScenarioTimingStats(
                    count=0,
                    mean_ms=0.0,
                    median_ms=0.0,
                    min_ms=0.0,
                    max_ms=0.0,
                    std_ms=0.0,
                ),
                llm_calls=LLMMetrics(
                    total=0,
                    by_model={},
                    tokens={
                        "prompt_total": 0,
                        "completion_total": 0,
                        "by_model": {},
                    },
                ),
                execution={
                    "completed": 0,
                    "failed": 0,
                    "retries": 0,
                    "retry_details": [],
                },
            )

    def test_schema_to_dict(self) -> None:
        """RunMetadataSchema converts to dictionary for JSON writing."""
        now = datetime.now(timezone.utc)
        metadata = RunMetadataSchema(
            run_id="run-123",
            eval_name="test",
            start_time_iso=now.isoformat() + "Z",
            end_time_iso=now.isoformat() + "Z",
            total_duration_seconds=60,
            scenario_timing=ScenarioTimingStats(
                count=5,
                mean_ms=1000.0,
                median_ms=1000.0,
                min_ms=1000.0,
                max_ms=1000.0,
                std_ms=0.0,
            ),
            llm_calls=LLMMetrics(
                total=5,
                by_model={"test-model": 5},
                tokens={
                    "prompt_total": 500,
                    "completion_total": 100,
                    "by_model": {
                        "test-model": {
                            "prompt": 500,
                            "completion": 100,
                        }
                    },
                },
            ),
            execution={
                "completed": 5,
                "failed": 0,
                "retries": 0,
                "retry_details": [],
            },
        )

        as_dict = metadata.model_dump()
        assert as_dict["run_id"] == "run-123"
        assert as_dict["total_duration_seconds"] == 60
