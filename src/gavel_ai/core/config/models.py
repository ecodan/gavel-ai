"""Pydantic models for configuration schemas."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class JudgeConfig(BaseModel):
    """Judge configuration."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    id: str = Field(..., description="Unique judge identifier")
    deepeval_name: str = Field(..., description="DeepEval judge type")
    config: Optional[Dict[str, Any]] = Field(None, description="Judge-specific config")
    config_ref: Optional[str] = Field(None, description="Path to external config file")


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

    eval_name: str
    eval_type: str  # "local" or "in-situ"
    processor_type: str
    scenarios_file: str
    agents_file: str
    judges_config: str
    output_dir: str
    judges: Optional[List[JudgeConfig]] = Field(None, description="Judge configurations")


class AsyncConfig(BaseModel):
    """Async execution configuration model."""

    model_config = ConfigDict(extra="ignore")  # Forward compatible

    max_workers: int = 4
    timeout_seconds: int = 30
    retry_count: int = 3
    error_handling: str = "fail_fast"  # or "continue"
