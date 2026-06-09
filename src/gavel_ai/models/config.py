"""Pydantic models for configuration schemas."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from gavel_ai.log_config import create_logger

logger = create_logger(__name__)


class ErrorPolicy(BaseModel):
    """Controls how the eval run responds to ERROR and WARNING-tier issues."""

    exit_on_error: bool = Field(True, description="Halt immediately on ERROR-tier issues")
    exit_on_warning: bool = Field(False, description="Halt immediately on WARNING-tier issues")

    def should_halt(self, tier: str) -> bool:
        """Return True if the given issue tier should halt the run under this policy."""
        return (tier == "ERROR" and self.exit_on_error) or (
            tier == "WARNING" and self.exit_on_warning
        )


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

    # External delegation fields (FR-7.1) — mirrors TestSubject's external transport shape.
    # When protocol is set the judge routes scoring to an external system rather than an LLM.
    protocol: Optional[Literal["http", "script"]] = Field(
        None,
        description="External transport protocol for delegated judging (http or script)",
    )
    system_id: Optional[str] = Field(
        None,
        description="External judge system identifier (used as judge_id in JudgedRecord)",
    )
    abort_on_exec_failure: bool = Field(
        True,
        description="Halt the run on PROCESS_FAILURE-tier outcomes from external judge",
    )
    abort_on_process_error: bool = Field(
        False,
        description="Halt the run on PROCESS_SUCCESS_WITH_ISSUE-tier outcomes from external judge",
    )
    # Reserved forward-compat seam (ADR-10): only "gavel" is implemented in this MVP.
    adapter: Optional[str] = Field(
        "gavel",
        description="Wire-format adapter identifier for external judge transport",
    )

    @model_validator(mode="after")
    def validate_external_judge_protocol_config(self) -> "JudgeConfig":
        """Validate protocol-specific config sub-shape for external judge configs."""
        if self.protocol == "http":
            if self.config is not None and "command" in self.config:
                raise ValueError(
                    "JudgeConfig.config for protocol='http' must not include 'command' "
                    "(that is a 'script' protocol field) - expected keys like "
                    "endpoint/method/headers/auth/trace_header"
                )
        elif self.protocol == "script":
            if self.config is not None and "endpoint" in self.config:
                raise ValueError(
                    "JudgeConfig.config for protocol='script' must not include 'endpoint' "
                    "(that is an 'http' protocol field) - expected keys like "
                    "command/args/working_dir/timeout/request_filename/response_filename"
                )
        return self


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
    # For external evaluations (test_subject_type='external')
    system_id: Optional[str] = Field(None, description="External system identifier")
    protocol: Optional[Literal["http", "script"]] = Field(
        None, description="External transport protocol (active when test_subject_type='external')"
    )
    config: Optional[Dict[str, Any]] = Field(None, description="External system config")
    abort_on_exec_failure: bool = Field(
        True, description="Halt the run on PROCESS_FAILURE-tier external outcomes"
    )
    abort_on_process_error: bool = Field(
        False, description="Halt the run on PROCESS_SUCCESS_WITH_ISSUE-tier external outcomes"
    )
    # Reserved forward-compat seam (ADR-10): only "gavel" is implemented in this MVP;
    # omitting it or passing "gavel" are equivalent and preserve current behavior exactly.
    adapter: Optional[str] = Field("gavel", description="Wire-format adapter identifier")

    @model_validator(mode="after")
    def validate_protocol_config(self) -> "TestSubject":
        """Validate protocol-specific `config` sub-shape for external test subjects."""
        if self.protocol == "http":
            if self.config is not None and "command" in self.config:
                raise ValueError(
                    "TestSubject.config for protocol='http' must not include 'command' "
                    "(that is a 'script' protocol field) - expected keys like "
                    "endpoint/method/headers/auth/trace_header"
                )
        elif self.protocol == "script":
            if self.config is not None and "endpoint" in self.config:
                raise ValueError(
                    "TestSubject.config for protocol='script' must not include 'endpoint' "
                    "(that is an 'http' protocol field) - expected keys like "
                    "command/args/working_dir/timeout/request_filename/response_filename"
                )
        return self


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


class TuningConfig(BaseModel):
    """Autotune optimization configuration."""

    model_config = ConfigDict(extra="ignore")

    max_rounds: int = Field(..., description="Hard upper bound on optimization iterations", ge=1)
    convergence_threshold: float = Field(
        0.02,
        description="Stop if |current_score - previous_score| < threshold (0.0-1.0 scale)",
        ge=0.0,
        le=1.0,
    )
    target_score: Optional[float] = Field(
        None,
        description="Stop early when avg_score reaches this value (0.0-1.0 scale)",
        ge=0.0,
        le=1.0,
    )
    degradation_tolerance: float = Field(
        0.05,
        description="Stop if avg_score drops by more than this amount (0.0-1.0 scale)",
        ge=0.0,
        le=1.0,
    )
    tuning_agent_model: str = Field(
        ..., description="Model ID from agents.json to use for TuningAgent"
    )
    tuning_agent_temperature: float = Field(
        0.7, description="Temperature for TuningAgent LLM calls", ge=0.0, le=2.0
    )


class IterationMetadata(BaseModel):
    """Per-iteration record persisted to iterations/iteration_N/metadata.json."""

    iteration: int
    prompt_version: str = Field(..., description='Prompt version used this iteration, e.g. "v1"')
    score: float = Field(..., description="Mean normalized score across all scenarios+judges (0.0-1.0)")
    improvement: float = Field(..., description="current_score - previous_score (0.0 for iteration 1)")
    judge_scores: Dict[str, float] = Field(
        default_factory=dict, description="Per-judge mean score breakdown: {judge_name: mean_score}"
    )
    converged: bool = False
    convergence_reason: Optional[str] = Field(
        None,
        description='One of "max_rounds_reached" | "target_score_achieved" | '
        '"minimal_improvement" | "performance_degraded" | None',
    )


class AutotuneRunSummary(BaseModel):
    """Run-level summary persisted to runs/<id>/run_summary.json and used by the reporter."""

    eval_name: str
    run_id: str
    total_iterations: int
    best_iteration: int
    best_score: float
    final_score: float
    converged: bool
    convergence_reason: Optional[str] = None
    iterations: List[IterationMetadata] = Field(default_factory=list)


class EvalConfig(BaseModel):
    """Evaluation configuration model."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)  # Forward compatible

    workflow_type: Literal["oneshot", "conversational", "autotune"] = Field(
        "oneshot", description="Type of evaluation workflow"
    )
    eval_type: str = Field(..., description="Evaluation type (oneshot, conversational, autotune)")
    eval_name: str = Field(..., description="Evaluation name")
    description: Optional[str] = Field(None, description="Evaluation description")
    test_subject_type: str = Field(..., description="Test subject type (local or external)")
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
    error_policy: ErrorPolicy = Field(
        default_factory=ErrorPolicy, description="Run error/warning policy"
    )
    tuning: Optional[TuningConfig] = Field(
        None, description="Autotune optimization configuration (required when workflow_type='autotune')"
    )

    @model_validator(mode="after")
    def validate_test_subject_type(self) -> "EvalConfig":
        """Accept 'local'/'external', and normalize the deprecated 'in-situ' alias.

        'in-situ' validates (for one minor version, per the migration plan) but is
        normalized internally to 'external' with a single WARNING-tier deprecation log.
        """
        if self.test_subject_type == "in-situ":
            logger.warning(
                "test_subject_type 'in-situ' is deprecated and has been normalized to "
                "'external' - update eval_config.json to use 'external' directly"
            )
            self.test_subject_type = "external"
        elif self.test_subject_type not in ("local", "external"):
            raise ValueError(
                f"test_subject_type must be one of 'local', 'external' (or the deprecated "
                f"alias 'in-situ') - got '{self.test_subject_type}'"
            )
        return self

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
