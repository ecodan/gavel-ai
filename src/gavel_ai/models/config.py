"""Pydantic models for configuration schemas."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class JudgeConfig(BaseModel):
    """Judge configuration for both config files and runtime usage."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Standard fields
    name: str = Field(..., description="Judge identifier (e.g., 'similarity', 'custom_accuracy')")
    type: str = Field(
        ..., description="Judge type (e.g., 'deepeval.similarity', 'custom.my_judge')"
    )

    # Configuration fields
    config: Optional[Dict[str, Any]] = Field(None, description="Judge-specific config dict")
    config_ref: Optional[str] = Field(None, description="Reference to external config file")
    threshold: Optional[float] = Field(None, description="Judge threshold for pass/fail (0.0-1.0)")
    model: Optional[str] = Field(None, description="LLM model for judge evaluation")

    # GEval-specific fields
    criteria: Optional[str] = Field(None, description="Evaluation criteria (for GEval judges)")
    evaluation_steps: Optional[List[str]] = Field(
        None, description="Evaluation steps (for GEval judges)"
    )


class ScenariosConfig(BaseModel):
    """Scenarios configuration."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    source: str = Field(..., description="Scenario source (file.local, file.remote, generator)")
    name: str = Field(..., description="Scenario name or file")


class ExecutionConfig(BaseModel):
    """Execution configuration."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    max_concurrent: int = Field(5, description="Maximum concurrent executions")


class AsyncConfig(BaseModel):
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

    model_config = ConfigDict(extra="ignore", populate_by_name=True)  # Forward compatible

    eval_type: str = Field(..., description="Evaluation type (oneshot, conversational, autotune)")
    eval_name: str = Field(..., description="Evaluation name")
    description: Optional[str] = Field(None, description="Evaluation description")
    test_subject_type: str = Field(..., description="Test subject type (local or remote)")
    test_subjects: List[TestSubject] = Field(..., description="Test subjects")
    variants: List[str] = Field(..., description="Variants to test")
    scenarios: ScenariosConfig = Field(..., description="Scenarios configuration")
    execution: Optional[ExecutionConfig] = Field(None, description="Execution configuration")
    async_config: Optional[AsyncConfig] = Field(
        None, alias="async", description="Async configuration"
    )


class AgentConfig(BaseModel):
    """Agent configuration referencing a model."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    model_id: str  # Reference to _models key
    prompt: str  # "prompt-name:version" format
    model_parameters: Optional[Dict[str, Any]] = None  # Override model params
    custom_configs: Optional[Dict[str, Any]] = None
