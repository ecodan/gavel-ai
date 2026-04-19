"""Pydantic models for configuration schemas."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


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

    # Markdown-based config loading
    markdown_path: Optional[str] = Field(
        None,
        description=(
            "Path to a Markdown file (relative to eval_dir) containing judge config sections: "
            "## Criteria, ## Evaluation Steps, ## Threshold, ## Guidelines"
        ),
    )


class ScenarioFieldMapping(BaseModel):
    """
    Maps scenario file fields (dot notation) to GEval LLMTestCase params.

    Each value is a dot-notation path resolved against the scenario object.
    Examples: "input.query", "metadata.expected_schema", "expected_behavior".

    - input / expected_output: resolved from the scenario file.
    - actual_output: if set, taken from the scenario (useful for re-judging
      pre-generated outputs); otherwise defaults to live processor output.
    """

    model_config = ConfigDict(extra="ignore")

    input: Optional[str] = Field(None, description="Dot-notation path to input text")
    expected_output: Optional[str] = Field(
        None, description="Dot-notation path to expected output text"
    )
    actual_output: Optional[str] = Field(
        None, description="Dot-notation path to actual output (overrides processor output)"
    )


class ScenariosConfig(BaseModel):
    """Scenarios configuration."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    source: str = Field(..., description="Scenario source (file.local, file.remote, generator)")
    name: str = Field(..., description="Scenario name or file")
    field_mapping: Optional[ScenarioFieldMapping] = Field(
        None,
        description=(
            "Maps scenario file fields to GEval test case params "
            "(input, expected_output, actual_output) using dot notation"
        ),
    )


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
    strict_mode: bool = Field(
        False,
        description="Return binary 0/1 score instead of continuous. Score normalizes to 1 or 10.",
    )


class TurnGeneratorConfig(BaseModel):
    """Configuration for turn generation in conversational evaluation."""

    model_config = ConfigDict(extra="ignore")

    model_id: str = Field(..., description="Model ID from agents.json for turn generation")
    temperature: float = Field(
        0.0, ge=0.0, le=2.0, description="Temperature for turn generation (0.0 for determinism)"
    )
    max_tokens: int = Field(500, ge=1, le=4000, description="Maximum tokens per generated turn")


class ElaborationConfig(BaseModel):
    """Configuration for scenario elaboration (GenerateStep)."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = Field(False, description="Whether to elaborate scenarios before execution")
    elaboration_template: Optional[str] = Field(
        None, description="Path to prompt template for elaboration"
    )
    model_id: Optional[str] = Field(
        None, description="Model ID for elaboration (defaults to turn_generator model)"
    )


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""

    model_config = ConfigDict(extra="ignore")

    max_retries: int = Field(3, ge=0, le=10, description="Maximum number of retry attempts")
    initial_delay_ms: int = Field(1000, ge=100, description="Initial delay in milliseconds")
    max_delay_ms: int = Field(30000, ge=1000, description="Maximum delay in milliseconds")
    backoff_factor: float = Field(2.0, ge=1.0, description="Exponential backoff factor")


class ConversationalConfig(BaseModel):
    """Configuration for conversational evaluation workflow."""

    model_config = ConfigDict(extra="ignore")

    max_turns: int = Field(
        10, ge=1, le=100, description="Maximum turns per conversation before termination"
    )
    max_turn_length: int = Field(2000, ge=100, le=10000, description="Maximum characters per turn")
    turn_generator: TurnGeneratorConfig = Field(
        ..., description="Configuration for turn generation"
    )
    elaboration: Optional[ElaborationConfig] = Field(
        None, description="Configuration for scenario elaboration"
    )
    max_duration_ms: int = Field(
        300000, ge=30000, le=3600000, description="Timeout for entire conversation execution"
    )
    retry_config: Optional[RetryConfig] = Field(
        default_factory=RetryConfig, description="Configuration for retry behavior"
    )


class EvalConfig(BaseModel):
    """Evaluation configuration model."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)  # Forward compatible

    workflow_type: Literal["oneshot", "conversational"] = Field(
        "oneshot", description="Type of evaluation workflow"
    )
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
    conversational: Optional[ConversationalConfig] = Field(
        None, description="Conversational evaluation configuration"
    )

    @model_validator(mode="after")
    def validate_conversational_config(self) -> "EvalConfig":
        """Ensure conversational config present when workflow_type is conversational."""
        if self.workflow_type == "conversational" and self.conversational is None:
            raise ValueError(
                "conversational config is required when workflow_type='conversational' - "
                "Add 'conversational' section with turn_generator configuration"
            )
        return self


class AgentConfig(BaseModel):
    """Agent configuration referencing a model."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    model_id: str  # Reference to _models key
    prompt: str  # "prompt-name:version" format
    model_parameters: Optional[Dict[str, Any]] = None  # Override model params
    custom_configs: Optional[Dict[str, Any]] = None
