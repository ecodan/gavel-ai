# Story C1.4: Extend eval_config.json for Conversational Settings

Status: ready-for-dev

## Story

As a user,
I want to configure conversational-specific settings in eval_config.json,
So that turn generation and elaboration behavior can be customized.

## Acceptance Criteria

1. **Given** eval_config.json includes "conversational" section
   **When** loaded
   **Then** it contains: max_turns (int), max_turn_length (int), turn_generator (model, temperature, max_tokens), elaboration (enabled, elaboration_template)

2. **Given** max_turns = 10
   **When** conversation executes
   **Then** loop terminates after 10 turns (or earlier if goal achieved)

3. **Given** turn_generator temperature = 0
   **When** same scenario runs twice
   **Then** identical turns are generated (deterministic)

4. **Given** elaboration.enabled = true
   **When** run includes --elaborate-scenarios flag
   **Then** GenerateStep is invoked before ConversationalProcessingStep

**Related Requirements:** FR-C1.1, FR-C2.2, NFR-C-R4 (Determinism)

## Tasks / Subtasks

- [ ] Task 1: Create TurnGeneratorConfig Pydantic model (AC: #1, #3)
  - [ ] 1.1: Define `TurnGeneratorConfig` model in `src/gavel_ai/models/config.py`
  - [ ] 1.2: Add `model_id: str` field referencing agents.json model (required)
  - [ ] 1.3: Add `temperature: float = 0.0` field (default 0 for determinism)
  - [ ] 1.4: Add `max_tokens: int = 500` field for turn generation limit
  - [ ] 1.5: Add validation for temperature range (0.0 to 2.0)

- [ ] Task 2: Create ElaborationConfig Pydantic model (AC: #1, #4)
  - [ ] 2.1: Define `ElaborationConfig` model in `src/gavel_ai/models/config.py`
  - [ ] 2.2: Add `enabled: bool = False` field
  - [ ] 2.3: Add `elaboration_template: Optional[str] = None` field (path to prompt template)
  - [ ] 2.4: Add `model_id: Optional[str] = None` field (model for elaboration, defaults to turn_generator)

- [ ] Task 3: Create ConversationalConfig Pydantic model (AC: #1, #2)
  - [ ] 3.1: Define `ConversationalConfig` model in `src/gavel_ai/models/config.py`
  - [ ] 3.2: Add `max_turns: int = 10` field with validation (1-100)
  - [ ] 3.3: Add `max_turn_length: int = 2000` field (character limit)
  - [ ] 3.4: Add `turn_generator: TurnGeneratorConfig` field (required)
  - [ ] 3.5: Add `elaboration: Optional[ElaborationConfig] = None` field
  - [ ] 3.6: Add `timeout_seconds: int = 300` field for conversation timeout

- [ ] Task 4: Extend EvalConfig with conversational settings (AC: #1)
  - [ ] 4.1: Add `conversational: Optional[ConversationalConfig] = None` to EvalConfig
  - [ ] 4.2: Add `workflow_type: Literal["oneshot", "conversational"] = "oneshot"` field
  - [ ] 4.3: Add validator to ensure conversational config present when workflow_type="conversational"

- [ ] Task 5: Export models from gavel_ai.models package (AC: #1)
  - [ ] 5.1: Update `src/gavel_ai/models/__init__.py` to export ConversationalConfig, TurnGeneratorConfig, ElaborationConfig
  - [ ] 5.2: Add to `__all__` list for clean imports

- [ ] Task 6: Write unit tests (AC: #1, #2, #3, #4)
  - [ ] 6.1: Create tests in `tests/unit/models/test_config.py` for new config models
  - [ ] 6.2: Test ConversationalConfig with all fields populated
  - [ ] 6.3: Test ConversationalConfig with only required fields (defaults)
  - [ ] 6.4: Test max_turns validation (1-100 range)
  - [ ] 6.5: Test temperature validation (0.0-2.0 range)
  - [ ] 6.6: Test EvalConfig with conversational section
  - [ ] 6.7: Test EvalConfig validation: conversational required when workflow_type="conversational"
  - [ ] 6.8: Test loading conversational config from JSON file

## Dev Notes

### Architecture Patterns & Constraints

**Model Location:** `src/gavel_ai/models/config.py` - Add to existing configuration models module.

**IMPORTANT:** The EvalConfig model already exists. We're EXTENDING it with a new optional `conversational` section.

**Pydantic Configuration (MANDATORY):**
```python
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TurnGeneratorConfig(BaseModel):
    """Configuration for turn generation in conversational evaluation."""
    model_config = ConfigDict(extra='ignore')

    model_id: str = Field(
        ...,
        description="Model ID from agents.json for turn generation"
    )
    temperature: float = Field(
        0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for turn generation (0.0 for determinism)"
    )
    max_tokens: int = Field(
        500,
        ge=1,
        le=4000,
        description="Maximum tokens per generated turn"
    )


class ElaborationConfig(BaseModel):
    """Configuration for scenario elaboration (GenerateStep)."""
    model_config = ConfigDict(extra='ignore')

    enabled: bool = Field(
        False,
        description="Whether to elaborate scenarios before execution"
    )
    elaboration_template: Optional[str] = Field(
        None,
        description="Path to prompt template for elaboration"
    )
    model_id: Optional[str] = Field(
        None,
        description="Model ID for elaboration (defaults to turn_generator model)"
    )


class ConversationalConfig(BaseModel):
    """Configuration for conversational evaluation workflow."""
    model_config = ConfigDict(extra='ignore')

    max_turns: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum turns per conversation before termination"
    )
    max_turn_length: int = Field(
        2000,
        ge=100,
        le=10000,
        description="Maximum characters per turn"
    )
    turn_generator: TurnGeneratorConfig = Field(
        ...,
        description="Configuration for turn generation"
    )
    elaboration: Optional[ElaborationConfig] = Field(
        None,
        description="Configuration for scenario elaboration"
    )
    timeout_seconds: int = Field(
        300,
        ge=30,
        le=3600,
        description="Timeout for entire conversation execution"
    )


# Extend existing EvalConfig (add these fields to existing model):
class EvalConfig(BaseModel):
    # ... existing fields ...

    workflow_type: Literal["oneshot", "conversational"] = Field(
        "oneshot",
        description="Type of evaluation workflow"
    )
    conversational: Optional[ConversationalConfig] = Field(
        None,
        description="Conversational evaluation configuration"
    )

    @model_validator(mode='after')
    def validate_conversational_config(self) -> 'EvalConfig':
        """Ensure conversational config present when workflow_type is conversational."""
        if self.workflow_type == "conversational" and self.conversational is None:
            raise ValueError(
                "conversational config is required when workflow_type='conversational' - "
                "Add 'conversational' section with turn_generator configuration"
            )
        return self
```

### Example eval_config.json with Conversational Settings

```json
{
  "workflow_type": "conversational",
  "name": "customer_support_eval",
  "description": "Evaluate customer support conversation quality",
  "judges": [
    {
      "id": "relevancy",
      "type": "turn",
      "deepeval_name": "deepeval.turn_relevancy"
    },
    {
      "id": "goal_achievement",
      "type": "conversation",
      "deepeval_name": "deepeval.conversation_completeness"
    }
  ],
  "conversational": {
    "max_turns": 15,
    "max_turn_length": 2000,
    "turn_generator": {
      "model_id": "claude-standard",
      "temperature": 0.0,
      "max_tokens": 500
    },
    "elaboration": {
      "enabled": false,
      "elaboration_template": "prompts/elaborate_scenarios.toml"
    },
    "timeout_seconds": 300
  }
}
```

### Backward Compatibility

- `workflow_type` defaults to `"oneshot"` for existing configs
- `conversational` is `Optional` so existing configs remain valid
- Only validate conversational presence when `workflow_type="conversational"`

### Testing Standards

- Tests go in `tests/unit/models/test_config.py`
- Use pytest fixtures from `conftest.py`
- Test all validation rules (ranges, required fields)
- Test backward compatibility with existing eval_config.json files
- Target >90% coverage on new config models

### References

- [Source: _bmad-output/planning-artifacts/epics-conversational-eval.md#Story C1.4]
- [Source: _bmad-output/planning-artifacts/project-context.md#Configuration & Startup]
- [Pattern: src/gavel_ai/models/config.py - Existing EvalConfig model]

## Dev Agent Record

### Agent Model Used

_To be filled during implementation_

### Debug Log References

_To be filled during implementation_

### Completion Notes List

_To be filled during implementation_

### File List

**Files to Modify:**
- `src/gavel_ai/models/config.py` - Add ConversationalConfig, TurnGeneratorConfig, ElaborationConfig; extend EvalConfig
- `src/gavel_ai/models/__init__.py` - Export new config models
- `tests/unit/models/test_config.py` - Add tests for new config models (or create if doesn't exist)

**Files Created:**
_None expected_
