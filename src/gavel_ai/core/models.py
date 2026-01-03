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
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


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

    id: str
    input: Dict[str, Any]
    expected_behavior: Optional[str] = Field(None, validation_alias="expected")
    metadata: Dict[str, Any] = {}

    @property
    def expected(self) -> Optional[str]:
        """Backward compatibility: access expected_behavior as expected."""
        return self.expected_behavior

    @property
    def scenario_id(self) -> str:
        """Backward compatibility: access id as scenario_id."""
        return self.id


class JudgeConfig(BaseModel):
    """
    Configuration model for judge instances.

    Uses extra='ignore' for forward compatibility - unknown fields are silently ignored.

    Per Architecture Decision 5: Contains judge type, threshold, and custom criteria
    for DeepEval-native judges with sequential execution.

    Supports both old and new schema:
    - Old: judge_id, judge_type, threshold, config dict
    - New: name, type, criteria, evaluation_steps, model, threshold
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # New schema fields (with backward compatibility)
    name: Optional[str] = Field(None, validation_alias="judge_id", description="Judge identifier")
    type: Optional[str] = Field(None, validation_alias="judge_type", description="Judge type")
    criteria: Optional[str] = Field(None, description="Evaluation criteria")
    evaluation_steps: Optional[List[str]] = Field(None, description="Evaluation steps")
    model: Optional[str] = Field(None, description="Model for judge evaluation")
    threshold: Optional[float] = Field(None, description="Pass/fail threshold (0.0-1.0)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Judge-specific config dict")

    # Legacy fields (deprecated)
    judge_id: Optional[str] = Field(None, description="[DEPRECATED] Use 'name' instead")
    judge_type: Optional[str] = Field(None, description="[DEPRECATED] Use 'type' instead")

    @property
    def judge_id_value(self) -> str:
        """Get judge_id from either name or judge_id field."""
        return self.name or self.judge_id or ""

    @property
    def judge_type_value(self) -> str:
        """Get judge_type from either type or judge_type field."""
        return self.type or self.judge_type or ""


class JudgeResult(BaseModel):
    """
    Result model from judge evaluation.

    Per Epic 4 Story 4.1: Contains score (1-10), reasoning, and evidence.
    All judges must produce scores on a consistent 1-10 scale for comparability.
    """

    model_config = ConfigDict(extra="ignore")

    score: int = Field(..., ge=1, le=10, description="Score from 1-10")
    reasoning: Optional[str] = Field(
        None, description="Optional explanation of the score"
    )
    evidence: Optional[str] = Field(
        None, description="Optional evidence supporting the score"
    )


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
    scenario_input: Dict[str, Any] = Field(
        ..., description="Original scenario input for re-judging"
    )
    expected_behavior: Optional[str] = Field(
        None, description="Expected behavior from scenario"
    )
    processor_output: str = Field(..., description="Output from processor")
    judges: list[JudgeEvaluation] = Field(
        default_factory=list, description="Judge evaluations"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


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
    config_hash: str = Field(
        ..., description="SHA-256 hash of all configs for reproducibility"
    )
    scenario_count: int = Field(..., description="Number of scenarios executed")
    variant_count: int = Field(..., description="Number of variants tested")
    judge_versions: List[Dict[str, str]] = Field(
        ..., description="List of judge versions used"
    )
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

    template_path: str = Field(
        ..., description="Path to template directory or file"
    )
    output_format: str = Field(
        ..., description="Output format: html, markdown, or json"
    )
    custom_vars: Optional[Dict[str, Any]] = Field(
        None, description="Custom variables for template rendering"
    )
