"""
Gavel-AI data models.

This module provides Pydantic models for configuration and runtime data.

Configuration Models (from config.py):
- EvalConfig: Evaluation configuration
- JudgeConfig: Judge configuration
- TestSubject: Test subject configuration
- ScenariosConfig: Scenario source configuration
- ExecutionConfig: Execution settings
- AsyncConfig: Async execution settings
- GEvalConfig: GEval judge configuration

Runtime Models (from runtime.py):
- Input: Input data for processing
- ProcessorConfig: Processor configuration
- ProcessorResult: Processor execution result
- Scenario: Test scenario
- JudgeResult: Judge evaluation result
- JudgeEvaluation: Judge ID + result combined
- EvaluationResult: Complete evaluation result with judges[]
- OutputRecord: Raw processor execution result
- JudgedRecord: Denormalized judge evaluation
- ArtifactRef: Reference to run artifacts
- Manifest: Run manifest for reproducibility
- ReporterConfig: Reporter configuration

Agent Models (from agents.py):
- ModelDefinition: Model definition for providers
- AgentConfig: Agent configuration
- AgentsFile: Complete agents.json structure

Utilities (from utils.py):
- validate_agent_references(): Validate agent model_id references
"""

# Configuration models
# Agent models
from gavel_ai.models.agents import (
    AgentConfig,
    AgentsFile,
    ModelDefinition,
)
from gavel_ai.models.config import (
    AsyncConfig,
    EvalConfig,
    GEvalConfig,
    JudgeConfig,
)

# Runtime models
from gavel_ai.models.runtime import (
    ArtifactRef,
    EvaluationResult,
    Input,
    JudgedRecord,
    JudgeEvaluation,
    JudgeResult,
    Manifest,
    OutputRecord,
    ProcessorConfig,
    ProcessorResult,
    ReporterConfig,
    Scenario,
)

# Utilities
from gavel_ai.models.utils import (
    validate_agent_references,
)

__all__ = [
    # Configuration models
    "AsyncConfig",
    "EvalConfig",
    "GEvalConfig",
    "JudgeConfig",
    # Runtime models
    "ArtifactRef",
    "EvaluationResult",
    "Input",
    "JudgeEvaluation",
    "JudgeResult",
    "JudgedRecord",
    "Manifest",
    "OutputRecord",
    "ProcessorConfig",
    "ProcessorResult",
    "ReporterConfig",
    "Scenario",
    # Agent models
    "AgentConfig",
    "AgentsFile",
    "ModelDefinition",
    # Utilities
    "validate_agent_references",
]
