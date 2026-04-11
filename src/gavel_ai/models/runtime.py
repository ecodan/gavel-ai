"""
Core data models for gavel-ai processors, judges, and reporters.

Defines Pydantic models for:
- Input: Input data for processing
- ProcessorConfig: Configuration for processor instances
- ProcessorResult: Results from processor execution
- Scenario: Test scenario with expected behavior
- JudgeConfig: Configuration for judge instances
- JudgeResult: Results from judge evaluation
- ReporterConfig: Configuration for reporter instances
- Manifest: Run manifest with metadata for reproducibility
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from gavel_ai.models.config import JudgeConfig  # noqa: F401


class Input(BaseModel):
    """
    Input data model for processor execution.

    Represents a single input to be processed, with associated metadata.
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    text: str
    metadata: Dict[str, Any] = {}


class ProcessorConfig(BaseModel):
    """
    Configuration model for processor instances.

    Uses extra='ignore' for forward compatibility - unknown fields are silently ignored.

    Per Architecture Decision 3: Contains behavioral rules for processors including
    async configuration, parallelism, error handling, and timeout settings.
    """

    model_config = ConfigDict(extra="ignore")

    processor_type: str
    parallelism: int = 1
    timeout_seconds: int = 30
    error_handling: str = "fail_fast"  # Options: fail_fast, continue_on_error, retry


class ProcessorResult(BaseModel):
    """
    Result model from processor execution.

    Contains output (any type), optional metadata, and optional error information.
    Output can be string, dict, list, or any JSON-serializable data.
    """

    model_config = ConfigDict(extra="ignore")

    output: Any
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None


class Scenario(BaseModel):
    """
    Test scenario model with input data and expected behavior.

    Represents a single test scenario to be evaluated, with input data
    and optional expected behavior for judge evaluation.

    Supports both old and new field names:
    - Old: id, input (dict), expected_behavior
    - New: scenario_id, input (string), expected
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str = Field(..., validation_alias=AliasChoices("id", "scenario_id"))
    input: Union[str, Dict[str, Any]]
    expected_behavior: Optional[str] = Field(
        None, validation_alias=AliasChoices("expected_behavior", "expected")
    )
    context: Optional[str] = None
    metadata: Dict[str, Any] = {}

    @property
    def expected(self) -> Optional[str]:
        """Backward compatibility: access expected_behavior as expected."""
        return self.expected_behavior

    @property
    def scenario_id(self) -> str:
        """Backward compatibility: access id as scenario_id."""
        return self.id


class JudgeResult(BaseModel):
    """
    Result model from judge evaluation.

    Per Epic 4 Story 4.1: Contains score (1-10), reasoning, and evidence.
    All judges must produce scores on a consistent 1-10 scale for comparability.
    """

    model_config = ConfigDict(extra="ignore")

    score: int = Field(..., ge=1, le=10, description="Score from 1-10")
    reasoning: Optional[str] = Field(None, description="Optional explanation of the score")
    evidence: Optional[str] = Field(None, description="Optional evidence supporting the score")


class JudgeEvaluation(BaseModel):
    """
    Single judge evaluation with judge_id and result.

    Per Epic 4 Story 4.5: Combines judge identifier with evaluation result
    for tracking multiple judge evaluations on the same output.
    """

    model_config = ConfigDict(extra="ignore")

    judge_id: str = Field(..., description="Judge identifier")
    score: int = Field(..., ge=1, le=10, description="Score from 1-10")
    reasoning: Optional[str] = Field(None, description="Explanation of the score")
    evidence: Optional[str] = Field(None, description="Evidence supporting the score")


class EvaluationResult(BaseModel):
    """
    Complete evaluation result with scenario, output, and all judge scores.

    Per Epic 4 Story 4.6: Result format for storage in results.jsonl.
    Contains all data needed for analysis and re-judging.
    """

    model_config = ConfigDict(extra="ignore")

    scenario_id: str = Field(..., description="Scenario identifier")
    variant_id: str = Field(..., description="Model/agent variant identifier")
    subject_id: str = Field(..., description="Subject identifier (PUT or SUT)")
    scenario_input: Union[str, Dict[str, Any]] = Field(
        ..., description="Original scenario input for re-judging"
    )
    expected_behavior: Optional[str] = Field(None, description="Expected behavior from scenario")
    processor_output: str = Field(..., description="Output from processor")
    judges: list[JudgeEvaluation] = Field(default_factory=list, description="Judge evaluations")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ArtifactRef(BaseModel):
    """
    Reference to a run artifact with metadata.

    Used by Run.artifacts property to describe available artifacts.
    """

    model_config = ConfigDict(extra="ignore")

    path: str = Field(..., description="Relative or absolute path to artifact")
    type: str = Field(..., description="Artifact type (json, jsonl, html, log, etc.)")
    size: int = Field(..., description="Size in bytes")


class Manifest(BaseModel):
    """
    Run manifest with metadata for reproducibility and tracking.

    Per FR-3.2 and FR-8.5: Captures run metadata including deterministic
    config hash for reproducibility verification.

    Per Story 6.5: Includes milestone marking to preserve important runs.

    Stored as manifest.json in run directory.
    """

    model_config = ConfigDict(extra="ignore")

    timestamp: datetime = Field(..., description="Run start time (ISO 8601)")
    config_hash: str = Field(..., description="SHA-256 hash of all configs for reproducibility")
    scenario_count: int = Field(..., description="Number of scenarios executed")
    variant_count: int = Field(..., description="Number of variants tested")
    judge_versions: List[Dict[str, str]] = Field(..., description="List of judge versions used")
    status: Literal["completed", "failed", "partial"] = Field(
        ..., description="Run completion status"
    )
    duration: float = Field(..., description="Total run time in seconds")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata key/value pairs"
    )
    is_milestone: bool = Field(
        default=False, description="Whether this run is marked as a milestone"
    )
    milestone_comment: Optional[str] = Field(
        None, description="Comment explaining why this is a milestone"
    )
    milestone_timestamp: Optional[datetime] = Field(
        None, description="When this run was marked as a milestone"
    )


class ReporterConfig(BaseModel):
    """
    Configuration model for reporter instances.

    Uses extra='ignore' for forward compatibility - unknown fields are silently ignored.

    Per Architecture Decision 8: Contains template path, output format, and custom
    variables for report generation.
    """

    model_config = ConfigDict(extra="ignore")

    template_path: str = Field(..., description="Path to template directory or file")
    output_format: str = Field(..., description="Output format: html, markdown, or json")
    custom_vars: Optional[Dict[str, Any]] = Field(
        None, description="Custom variables for template rendering"
    )


class OutputRecord(BaseModel):
    """
    Single raw processor execution result.

    Per Data Schemas Specification: Raw execution result before judging.
    Used in results_raw.jsonl storage.

    Field mapping from EvaluationResult:
    - subject_id → test_subject (per spec naming)
    - Added: timing_ms, tokens_prompt, tokens_completion, error
    - Removed: judges[], scenario_input, expected_behavior (only raw result)
    """

    model_config = ConfigDict(extra="ignore")

    test_subject: str = Field(..., description="Test subject identifier (prompt name or system ID)")
    variant_id: str = Field(..., description="Model variant ID used for execution")
    scenario_id: str = Field(..., description="Scenario identifier")
    processor_output: str = Field(..., description="Raw output from processor/model")
    timing_ms: int = Field(..., ge=0, description="Execution time in milliseconds")
    tokens_prompt: int = Field(..., ge=0, description="Prompt tokens consumed")
    tokens_completion: int = Field(..., ge=0, description="Completion tokens generated")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (e.g. turn_number)"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp of execution")


class JudgedRecord(BaseModel):
    """
    Single judge evaluation result.

    Per Data Schemas Specification: Denormalized judge evaluation.
    One OutputRecord can have multiple JudgedRecords (one per judge).
    Used in results_judged.jsonl storage.

    Joins with OutputRecord on (test_subject, variant_id, scenario_id).
    """

    model_config = ConfigDict(extra="ignore")

    test_subject: str = Field(..., description="Test subject identifier")
    variant_id: str = Field(..., description="Model variant ID")
    scenario_id: str = Field(..., description="Scenario identifier")
    judge_id: str = Field(..., description="Judge name from eval config")
    score: int = Field(..., ge=1, le=10, description="Score from 1-10 (normalized scale)")
    reasoning: Optional[str] = Field(None, description="Judge's explanation (null if error)")
    error: Optional[str] = Field(None, description="Error message if judging failed")
    timestamp: str = Field(..., description="ISO 8601 timestamp of evaluation")


class Turn(BaseModel):
    """
    Standardized conversation turn for reporting.
    """

    model_config = ConfigDict(extra="ignore")

    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., description="Text content of the turn")
    duration_ms: float = Field(0.0, description="Duration in milliseconds")
    timestamp: datetime = Field(default_factory=datetime.now)


class VariantResult(BaseModel):
    """
    Comparison variant result for a specific scenario.
    """

    model_config = ConfigDict(extra="ignore")

    variant_id: str
    turns: List[Turn] = Field(default_factory=list)
    judgments: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    output: Optional[str] = None
    timing: Dict[str, float] = Field(default_factory=dict)


class ScenarioResult(BaseModel):
    """
    Scenario-level aggregation of variants for comparison.
    """

    model_config = ConfigDict(extra="ignore")

    scenario_id: str
    system_input: Optional[str] = None
    test_subject: Optional[str] = None
    variants: Dict[str, VariantResult] = Field(default_factory=dict)


class ReportData(BaseModel):
    """
    Unified evaluation report data structure.
    """

    model_config = ConfigDict(extra="ignore")

    title: str
    run_id: str
    generated_at: datetime = Field(default_factory=datetime.now)
    summary_metrics: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    performance_metrics: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    scenarios: List[ScenarioResult] = Field(default_factory=list)
    scenarios_by_subject: Dict[str, List[ScenarioResult]] = Field(default_factory=dict)
