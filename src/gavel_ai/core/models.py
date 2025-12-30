"""
Core data models for gavel-ai processors and judges.

Defines Pydantic models for:
- Input: Input data for processing
- ProcessorConfig: Configuration for processor instances
- ProcessorResult: Results from processor execution
- Scenario: Test scenario with expected behavior
- JudgeConfig: Configuration for judge instances
- JudgeResult: Results from judge evaluation
"""

from typing import Any, Dict, Optional

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
    """

    model_config = ConfigDict(extra="ignore")

    id: str
    input: Dict[str, Any]
    expected_behavior: Optional[str] = None
    metadata: Dict[str, Any] = {}


class JudgeConfig(BaseModel):
    """
    Configuration model for judge instances.

    Uses extra='ignore' for forward compatibility - unknown fields are silently ignored.

    Per Architecture Decision 5: Contains judge type, threshold, and custom criteria
    for DeepEval-native judges with sequential execution.
    """

    model_config = ConfigDict(extra="ignore")

    judge_id: str
    judge_type: str  # e.g., "deepeval.similarity", "deepeval.geval", "custom"
    threshold: Optional[float] = None
    config: Dict[str, Any] = {}


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
