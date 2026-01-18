# Story C1.1: Define Conversational Scenario Schema

Status: done

## Story

As a developer,
I want scenarios to support user_goal, context, and dialogue_guidance,
So that turn generation can be realistic and context-aware.

## Acceptance Criteria

1. **Given** a scenarios.json file exists with conversational scenarios
   **When** it is loaded
   **Then** each scenario has: id (required), user_goal (required), context (optional), dialogue_guidance (optional)

2. **Given** a scenario defines user_goal
   **When** examined
   **Then** it's a clear, actionable description of what the simulated user is trying to accomplish

3. **Given** dialogue_guidance is defined
   **When** examined
   **Then** it contains: tone_preference, escalation_strategy, factual_constraints

4. **Given** scenarios are loaded
   **When** validated
   **Then** missing user_goal raises ValidationError with clear guidance

**Related Requirements:** FR-C1.1, NFR-C-R1 (Reproducibility)

## Tasks / Subtasks

- [x] Task 1: Create ConversationScenario Pydantic model (AC: #1, #2, #3, #4)
  - [x] 1.1: Create `src/gavel_ai/models/conversation.py` module
  - [x] 1.2: Define `DialogueGuidance` nested model with tone_preference, escalation_strategy, factual_constraints fields
  - [x] 1.3: Define `ConversationScenario` model with: scenario_id, user_goal (required), context (optional), dialogue_guidance (optional)
  - [x] 1.4: Add field validators for user_goal (ensure non-empty, meaningful)
  - [x] 1.5: Configure model with `ConfigDict(extra='ignore')` for forward compatibility
  - [x] 1.6: Add backward-compatible `id` property (like existing Scenario model)

- [x] Task 2: Implement scenario loading and validation (AC: #1, #4)
  - [x] 2.1: Implemented as utility functions in conversation.py (using existing RecordDataSource pattern)
  - [x] 2.2: Implement `load_conversation_scenarios(path: Path) -> List[ConversationScenario]` function
  - [x] 2.3: Add validation error with clear message via Pydantic validator + loader wrapper
  - [x] 2.4: Support both `.json` and `.jsonl` file formats

- [x] Task 3: Export models from gavel_ai.models package (AC: #1)
  - [x] 3.1: Update `src/gavel_ai/models/__init__.py` to export ConversationScenario, DialogueGuidance
  - [x] 3.2: Add to `__all__` list for clean imports

- [x] Task 4: Write unit tests (AC: #1, #2, #3, #4)
  - [x] 4.1: Create `tests/unit/test_conversation.py` (36 tests)
  - [x] 4.2: Test ConversationScenario with all fields populated
  - [x] 4.3: Test ConversationScenario with only required fields (user_goal)
  - [x] 4.4: Test ValidationError raised when user_goal missing
  - [x] 4.5: Test DialogueGuidance nested model
  - [x] 4.6: Test scenario loading from JSON file
  - [x] 4.7: Test scenario loading from JSONL file

### Review Follow-ups (AI)

- [ ] [AI-Review][MEDIUM] Fix docstring: claims ValidationError raised but code raises ValueError [conversation.py:107]
- [ ] [AI-Review][MEDIUM] Remove unused import `tempfile` [test_conversation.py:6]
- [ ] [AI-Review][MEDIUM] Change `List[dict]` to `List[Dict[str, Any]]` for type consistency [conversation.py:125]
- [ ] [AI-Review][LOW] Add `__all__` to module for explicit public API declaration [conversation.py]
- [ ] [AI-Review][LOW] Extract file existence check to helper to reduce duplication [conversation.py:116-119,179-182]
- [ ] [AI-Review][LOW] Update docstring: note JSON falls back to non-streaming load [conversation.py:164-176]
- [ ] [AI-Review][LOW] Add test case for explicit `user_goal=None` [test_conversation.py]

## Dev Notes

### Architecture Patterns & Constraints

**Model Location:** `src/gavel_ai/models/conversation.py` - New module for conversational-specific models. Follow existing pattern from `src/gavel_ai/models/scenarios.py`.

**Pydantic Configuration (MANDATORY):**
```python
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ConversationScenario(BaseModel):
    model_config = ConfigDict(extra='ignore', populate_by_name=True)
    # ... fields
```

**Field Naming:**
- Use `snake_case` for all fields
- Use `Field(..., validation_alias="id")` pattern for backward compatibility (see existing Scenario model)

**Error Message Format (MANDATORY):**
```
<ErrorType>: <What happened> - <Recovery step>
```
Example: `ValidationError: Missing required field 'user_goal' in scenario - Add a description of what the simulated user is trying to accomplish`

**Existing Pattern to Follow:** See `src/gavel_ai/models/scenarios.py:8-51` for the existing `Scenario` model pattern. ConversationScenario should follow the same structure.

### DialogueGuidance Schema

```python
class DialogueGuidance(BaseModel):
    """Guidance for turn generation behavior."""
    model_config = ConfigDict(extra='ignore')

    tone_preference: Optional[str] = Field(
        None,
        description="Desired tone: professional, casual, frustrated, confused, etc."
    )
    escalation_strategy: Optional[str] = Field(
        None,
        description="How user should escalate if goal not met: politely insist, express frustration, ask for supervisor, etc."
    )
    factual_constraints: Optional[List[str]] = Field(
        None,
        description="Facts the simulated user knows and may reference"
    )
```

### ConversationScenario Schema

```python
class ConversationScenario(BaseModel):
    """Conversational scenario for multi-turn evaluation."""
    model_config = ConfigDict(extra='ignore', populate_by_name=True)

    scenario_id: str = Field(
        ...,
        validation_alias="id",
        description="Unique scenario identifier"
    )
    user_goal: str = Field(
        ...,
        description="Clear, actionable description of what the simulated user is trying to accomplish"
    )
    context: Optional[str] = Field(
        None,
        description="Background context for the conversation"
    )
    dialogue_guidance: Optional[DialogueGuidance] = Field(
        None,
        description="Guidance for turn generation behavior"
    )

    @field_validator('user_goal', mode='before')
    @classmethod
    def validate_user_goal(cls, v: Any) -> str:
        if not v or (isinstance(v, str) and not v.strip()):
            raise ValueError(
                "user_goal cannot be empty - Provide a clear description of what the simulated user is trying to accomplish"
            )
        return v

    @property
    def id(self) -> str:
        """Backward compatibility: access scenario_id as id."""
        return self.scenario_id
```

### Example scenarios.json Format

```json
[
  {
    "id": "booking_flight",
    "user_goal": "Book a round-trip flight from NYC to LAX for next weekend, preferring morning departures",
    "context": "User is a frequent flyer with airline loyalty status",
    "dialogue_guidance": {
      "tone_preference": "professional but time-pressed",
      "escalation_strategy": "politely insist if initial options don't meet preferences",
      "factual_constraints": ["Budget is $500 max", "Must arrive by 2pm local time"]
    }
  },
  {
    "id": "simple_inquiry",
    "user_goal": "Find out store hours for the downtown location"
  }
]
```

### Project Structure Notes

**Files to Create:**
- `src/gavel_ai/models/conversation.py` - ConversationScenario, DialogueGuidance models
- `tests/unit/models/test_conversation.py` - Unit tests

**Files to Modify:**
- `src/gavel_ai/models/__init__.py` - Export new models

**Alignment with Unified Project Structure:**
- Models go in `src/gavel_ai/models/` (not `core/models.py`)
- Tests mirror source structure: `tests/unit/models/test_conversation.py`
- Follow existing naming: `conversation.py` matches pattern of `scenarios.py`, `runtime.py`

### Type Hints (MANDATORY)

All functions MUST have complete type hints:
```python
from typing import Any, Dict, List, Optional
from pathlib import Path

def load_scenarios(path: Path) -> List[ConversationScenario]:
    """Load conversational scenarios from file."""
    ...
```

### Testing Standards

- Tests go in `tests/unit/models/test_conversation.py`
- Use pytest fixtures from `conftest.py`
- Mock file I/O where appropriate
- Target >90% coverage on new models

### References

- [Source: _bmad-output/planning-artifacts/epics-conversational-eval.md#Story C1.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data Model Patterns]
- [Source: _bmad-output/planning-artifacts/project-context.md#Type Hints & Validation]
- [Pattern: src/gavel_ai/models/scenarios.py - Existing Scenario model]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - All tests passed on first run

### Completion Notes List

1. Created `src/gavel_ai/models/conversation.py` with DialogueGuidance and ConversationScenario Pydantic models
2. Implemented loader functions `load_conversation_scenarios()` and `iter_conversation_scenarios()` for JSON/JSONL support
3. Updated `src/gavel_ai/models/__init__.py` to export new models and functions
4. Created comprehensive test suite with 36 tests covering all acceptance criteria
5. All tests pass (36/36)
6. Ruff linting passes

### File List

**Files Created:**
- `src/gavel_ai/models/conversation.py` - ConversationScenario and DialogueGuidance models with loader functions
- `tests/unit/test_conversation.py` - 36 unit tests for models and loaders

**Files Modified:**
- `src/gavel_ai/models/__init__.py` - Added exports for ConversationScenario, DialogueGuidance, load_conversation_scenarios, iter_conversation_scenarios
