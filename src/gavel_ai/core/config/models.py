"""Pydantic models for configuration schemas."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class JudgeConfig(BaseModel):
    """Judge configuration for config file loading."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)  # Forward compatible

    id: str = Field(..., description="Judge identifier")
    deepeval_name: str = Field(..., description="DeepEval judge type (e.g., deepeval.geval)")
    config: Optional[Dict[str, Any]] = Field(None, description="Judge-specific config dict")
    config_ref: Optional[str] = Field(None, description="Reference to external config file")


class ScenariosConfig(BaseModel):
    """Scenarios configuration."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    source: str = Field(..., description="Scenario source (file.local, file.remote, generator)")
    name: str = Field(..., description="Scenario name or file")


class ExecutionConfig(BaseModel):
    """Execution configuration."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    max_concurrent: int = Field(5, description="Maximum concurrent executions")


class AsyncConfigNew(BaseModel):
    """Async execution configuration (new schema)."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    num_workers: int = Field(8, description="Number of worker tasks")
    arrival_rate_per_sec: float = Field(20.0, description="Arrival rate per second")
    exec_rate_per_min: int = Field(100, description="Execution rate per minute")
    max_retries: int = Field(3, description="Maximum retries")
    task_timeout_seconds: int = Field(300, description="Task timeout in seconds")
    stuck_timeout_seconds: int = Field(600, description="Stuck timeout in seconds")
    emit_progress_interval_sec: int = Field(10, description="Progress emission interval")


class TestSubject(BaseModel):
    """Test subject configuration (local prompt-based)."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    prompt_name: Optional[str] = Field(None, description="Prompt template name")
    judges: List[JudgeConfig] = Field(..., description="Judges for this test subject")
    # For remote (closed-box) evaluations
    system_id: Optional[str] = Field(None, description="Remote system identifier")
    protocol: Optional[str] = Field(None, description="Protocol (acp, open_ai)")
    config: Optional[Dict[str, Any]] = Field(None, description="Remote system config")


class GEvalConfig(BaseModel):
    """Custom GEval judge configuration."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    criteria: str = Field(..., description="Evaluation criteria")
    evaluation_steps: List[str] = Field(..., description="Evaluation steps")
    model: str = Field(..., description="LLM model for evaluation")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Pass/fail threshold")


class EvalConfig(BaseModel):
    """Evaluation configuration model."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    eval_type: str = Field(..., description="Evaluation type (oneshot, conversational, autotune)")
    eval_name: str = Field(..., description="Evaluation name")
    description: Optional[str] = Field(None, description="Evaluation description")
    # New schema fields (all optional for backward compatibility)
    test_subject_type: Optional[str] = Field(None, description="Test subject type (local or remote)")
    test_subjects: Optional[List[TestSubject]] = Field(None, description="Test subjects")
    variants: Optional[List[str]] = Field(None, description="Variants to test")
    scenarios: Optional[ScenariosConfig] = Field(None, description="Scenarios configuration")
    execution: Optional[ExecutionConfig] = Field(None, description="Execution configuration")
    async_config: Optional[AsyncConfigNew] = Field(None, alias="async", description="Async configuration")
    # Keep old fields optional for backward compatibility
    processor_type: Optional[str] = Field(None, description="[DEPRECATED] Processor type")
    scenarios_file: Optional[str] = Field(None, description="[DEPRECATED] Scenarios file")
    agents_file: Optional[str] = Field(None, description="[DEPRECATED] Agents file")
    judges_config: Optional[str] = Field(None, description="[DEPRECATED] Judges config")
    output_dir: Optional[str] = Field(None, description="[DEPRECATED] Output directory")
    judges: Optional[List[JudgeConfig]] = Field(None, description="[DEPRECATED] Judge configurations")


class AsyncConfig(BaseModel):
    """Async execution configuration model (legacy schema)."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    max_workers: int = 4
    timeout_seconds: int = 30
    retry_count: int = 3
    error_handling: str = "fail_fast"  # or "continue"
