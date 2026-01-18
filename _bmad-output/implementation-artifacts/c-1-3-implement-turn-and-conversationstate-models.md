# Story C1.3: Implement Turn and ConversationState Models

Status: ready-for-dev

## Story

As a developer,
I want Turn and ConversationState models to manage dialogue history,
So that turns can be tracked and conversation state maintained during execution.

## Acceptance Criteria

1. **Given** Turn model exists
   **When** examined
   **Then** it has: turn_number (int), role (user|assistant), content (str), timestamp (datetime), metadata (dict, optional)

2. **Given** ConversationState is initialized
   **When** examined
   **Then** it has: scenario_id, variant_id, turns (list), start_time, metadata

3. **Given** add_turn(role, content) is called
   **When** completed
   **Then** Turn is appended to turns list with auto-incremented turn_number and current timestamp

4. **Given** conversation has multiple turns
   **When** history property is accessed
   **Then** formatted string is returned: "user: content\nassistant: content\nuser: content..."

5. **Given** metadata is provided with a turn
   **When** stored
   **Then** tokens_prompt, tokens_completion, latency_ms can be accessed

**Related Requirements:** FR-C2.3, NFR-C-R1 (Reproducibility)

## Tasks / Subtasks

- [ ] Task 1: Create Turn Pydantic model (AC: #1, #5)
  - [ ] 1.1: Define `Turn` model in `src/gavel_ai/models/conversation.py`
  - [ ] 1.2: Add `turn_number: int` field (0-indexed)
  - [ ] 1.3: Add `role: Literal["user", "assistant"]` field with validation
  - [ ] 1.4: Add `content: str` field (required, non-empty)
  - [ ] 1.5: Add `timestamp: datetime` field with default factory `datetime.utcnow`
  - [ ] 1.6: Add `metadata: Optional[TurnMetadata]` field for tokens/latency

- [ ] Task 2: Create TurnMetadata nested model (AC: #5)
  - [ ] 2.1: Define `TurnMetadata` model for turn-level metrics
  - [ ] 2.2: Add `tokens_prompt: Optional[int]` field
  - [ ] 2.3: Add `tokens_completion: Optional[int]` field
  - [ ] 2.4: Add `latency_ms: Optional[int]` field
  - [ ] 2.5: Add `extra: Optional[Dict[str, Any]]` for extensibility

- [ ] Task 3: Create ConversationState model (AC: #2, #3, #4)
  - [ ] 3.1: Define `ConversationState` model in `src/gavel_ai/models/conversation.py`
  - [ ] 3.2: Add `scenario_id: str` field (required)
  - [ ] 3.3: Add `variant_id: str` field (required)
  - [ ] 3.4: Add `turns: List[Turn]` field with default empty list
  - [ ] 3.5: Add `start_time: datetime` field with default factory
  - [ ] 3.6: Add `metadata: Optional[Dict[str, Any]]` field

- [ ] Task 4: Implement add_turn method on ConversationState (AC: #3)
  - [ ] 4.1: Implement `add_turn(role: str, content: str, metadata: Optional[TurnMetadata] = None) -> Turn`
  - [ ] 4.2: Auto-increment turn_number based on existing turns count
  - [ ] 4.3: Set timestamp to current UTC time
  - [ ] 4.4: Append Turn to turns list
  - [ ] 4.5: Return the created Turn for reference

- [ ] Task 5: Implement history property on ConversationState (AC: #4)
  - [ ] 5.1: Implement `history` property returning formatted string
  - [ ] 5.2: Format: "user: content\nassistant: content\n..."
  - [ ] 5.3: Handle empty turns list gracefully (return empty string)

- [ ] Task 6: Export models from gavel_ai.models package (AC: #1, #2)
  - [ ] 6.1: Update `src/gavel_ai/models/__init__.py` to export Turn, TurnMetadata, ConversationState
  - [ ] 6.2: Add to `__all__` list for clean imports

- [ ] Task 7: Write unit tests (AC: #1, #2, #3, #4, #5)
  - [ ] 7.1: Create tests in `tests/unit/test_conversation.py` for new models
  - [ ] 7.2: Test Turn model with all fields populated
  - [ ] 7.3: Test Turn model with only required fields
  - [ ] 7.4: Test Turn role validation (only "user" or "assistant")
  - [ ] 7.5: Test TurnMetadata with token counts and latency
  - [ ] 7.6: Test ConversationState initialization
  - [ ] 7.7: Test add_turn auto-increments turn_number
  - [ ] 7.8: Test add_turn sets timestamp
  - [ ] 7.9: Test history property formatting
  - [ ] 7.10: Test history property with empty turns

## Dev Notes

### Architecture Patterns & Constraints

**Model Location:** `src/gavel_ai/models/conversation.py` - Add to existing conversational models module.

**Pydantic Configuration (MANDATORY):**
```python
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TurnMetadata(BaseModel):
    """Metadata for a single conversation turn."""
    model_config = ConfigDict(extra='ignore')

    tokens_prompt: Optional[int] = Field(
        None,
        description="Number of prompt tokens for this turn"
    )
    tokens_completion: Optional[int] = Field(
        None,
        description="Number of completion tokens for this turn"
    )
    latency_ms: Optional[int] = Field(
        None,
        description="Latency in milliseconds for this turn"
    )
    extra: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for extensibility"
    )


class Turn(BaseModel):
    """A single turn in a conversation."""
    model_config = ConfigDict(extra='ignore')

    turn_number: int = Field(
        ...,
        ge=0,
        description="Zero-indexed turn number"
    )
    role: Literal["user", "assistant"] = Field(
        ...,
        description="Role of the speaker: user or assistant"
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Content of the turn"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when turn was created"
    )
    metadata: Optional[TurnMetadata] = Field(
        None,
        description="Optional metadata (tokens, latency)"
    )


class ConversationState(BaseModel):
    """State of a multi-turn conversation."""
    model_config = ConfigDict(extra='ignore')

    scenario_id: str = Field(
        ...,
        description="ID of the scenario being executed"
    )
    variant_id: str = Field(
        ...,
        description="ID of the variant (model/config) being tested"
    )
    turns: List[Turn] = Field(
        default_factory=list,
        description="List of conversation turns"
    )
    start_time: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when conversation started"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional conversation metadata"
    )

    def add_turn(
        self,
        role: Literal["user", "assistant"],
        content: str,
        metadata: Optional[TurnMetadata] = None
    ) -> Turn:
        """Add a new turn to the conversation.

        Args:
            role: Speaker role ("user" or "assistant")
            content: Turn content
            metadata: Optional turn metadata

        Returns:
            The created Turn object
        """
        turn = Turn(
            turn_number=len(self.turns),
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            metadata=metadata
        )
        self.turns.append(turn)
        return turn

    @property
    def history(self) -> str:
        """Get formatted conversation history.

        Returns:
            String formatted as "user: content\\nassistant: content\\n..."
        """
        if not self.turns:
            return ""
        return "\n".join(f"{turn.role}: {turn.content}" for turn in self.turns)
```

### Example Usage

```python
# Create conversation state
state = ConversationState(
    scenario_id="booking_flight",
    variant_id="claude-3.5-sonnet"
)

# Add turns
state.add_turn("user", "I want to book a flight to NYC")
state.add_turn("assistant", "I'd be happy to help you book a flight to NYC. What dates are you looking at?")
state.add_turn("user", "Next weekend, departing Friday", metadata=TurnMetadata(latency_ms=150))

# Get formatted history
print(state.history)
# Output:
# user: I want to book a flight to NYC
# assistant: I'd be happy to help you book a flight to NYC. What dates are you looking at?
# user: Next weekend, departing Friday
```

### Testing Standards

- Tests go in existing `tests/unit/test_conversation.py`
- Use pytest fixtures from `conftest.py`
- Test all validation rules (role values, content non-empty)
- Test edge cases (empty history, single turn)
- Target >90% coverage on new models

### References

- [Source: _bmad-output/planning-artifacts/epics-conversational-eval.md#Story C1.3]
- [Source: _bmad-output/planning-artifacts/project-context.md#Type Hints & Validation]
- [Pattern: src/gavel_ai/models/conversation.py - Existing models]
- [Pattern: src/gavel_ai/models/runtime.py - ProcessorResult for metadata patterns]

## Dev Agent Record

### Agent Model Used

_To be filled during implementation_

### Debug Log References

_To be filled during implementation_

### Completion Notes List

_To be filled during implementation_

### File List

**Files to Modify:**
- `src/gavel_ai/models/conversation.py` - Add Turn, TurnMetadata, ConversationState models
- `src/gavel_ai/models/__init__.py` - Export new models
- `tests/unit/test_conversation.py` - Add tests for new models

**Files Created:**
_None expected_
