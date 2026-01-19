# Story C1.3: Implement Turn and ConversationState Models

Status: done

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

- [x] Task 1: Create Turn Pydantic model (AC: #1, #5)
  - [x] 1.1: Define `Turn` model in `src/gavel_ai/models/conversation.py`
  - [x] 1.2: Add `turn_number: int` field (0-indexed)
  - [x] 1.3: Add `role: Literal["user", "assistant"]` field with validation
  - [x] 1.4: Add `content: str` field (required, non-empty)
  - [x] 1.5: Add `timestamp: datetime` field with default factory `datetime.utcnow`
  - [x] 1.6: Add `metadata: Optional[TurnMetadata]` field for tokens/latency

- [x] Task 2: Create TurnMetadata nested model (AC: #5)
  - [x] 2.1: Define `TurnMetadata` model for turn-level metrics
  - [x] 2.2: Add `tokens_prompt: Optional[int]` field
  - [x] 2.3: Add `tokens_completion: Optional[int]` field
  - [x] 2.4: Add `latency_ms: Optional[int]` field
  - [x] 2.5: Add `extra: Optional[Dict[str, Any]]` for extensibility

- [x] Task 3: Create ConversationState model (AC: #2, #3, #4)
  - [x] 3.1: Define `ConversationState` model in `src/gavel_ai/models/conversation.py`
  - [x] 3.2: Add `scenario_id: str` field (required)
  - [x] 3.3: Add `variant_id: str` field (required)
  - [x] 3.4: Add `turns: List[Turn]` field with default empty list
  - [x] 3.5: Add `start_time: datetime` field with default factory
  - [x] 3.6: Add `metadata: Optional[Dict[str, Any]]` field

- [x] Task 4: Implement add_turn method on ConversationState (AC: #3)
  - [x] 4.1: Implement `add_turn(role: str, content: str, metadata: Optional[TurnMetadata] = None) -> Turn`
  - [x] 4.2: Auto-increment turn_number based on existing turns count
  - [x] 4.3: Set timestamp to current UTC time
  - [x] 4.4: Append Turn to turns list
  - [x] 4.5: Return the created Turn for reference

- [x] Task 5: Implement history property on ConversationState (AC: #4)
  - [x] 5.1: Implement `history` property returning formatted string
  - [x] 5.2: Format: "user: content\nassistant: content\n..."
  - [x] 5.3: Handle empty turns list gracefully (return empty string)

- [x] Task 6: Export models from gavel_ai.models package (AC: #1, #2)
  - [x] 6.1: Update `src/gavel_ai/models/__init__.py` to export Turn, TurnMetadata, ConversationState
  - [x] 6.2: Add to `__all__` list for clean imports

- [x] Task 7: Write unit tests (AC: #1, #2, #3, #4, #5)
  - [x] 7.1: Create tests in `tests/unit/test_conversation.py` for new models
  - [x] 7.2: Test Turn model with all fields populated
  - [x] 7.3: Test Turn model with only required fields
  - [x] 7.4: Test Turn role validation (only "user" or "assistant")
  - [x] 7.5: Test TurnMetadata with token counts and latency
  - [x] 7.6: Test ConversationState initialization
  - [x] 7.7: Test add_turn auto-increments turn_number
  - [x] 7.8: Test add_turn sets timestamp
  - [x] 7.9: Test history property formatting
  - [x] 7.10: Test history property with empty turns

### Review Follow-ups (AI)

- [ ] [AI-Review][MEDIUM] Inconsistent whitespace validation - Turn.content uses min_length=1 but allows whitespace-only content, unlike ConversationScenario.user_goal which validates against whitespace [conversation.py:139-142]
- [ ] [AI-Review][MEDIUM] Missing serialization round-trip tests - No tests verify model_dump_json() / model_validate_json() [test_conversation.py]
- [ ] [AI-Review][MEDIUM] Missing error message test for add_turn with empty content [test_conversation.py]
- [ ] [AI-Review][LOW] Missing convenience properties - TurnMetadata.total_tokens, ConversationState.turn_count [conversation.py]
- [ ] [AI-Review][LOW] Models not frozen for immutability - Turn should arguably be immutable once created [conversation.py]

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

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

No debug issues encountered during implementation.

### Completion Notes List

- Implemented TurnMetadata model with tokens_prompt, tokens_completion, latency_ms, and extra fields
- Implemented Turn model with turn_number (0-indexed, ge=0), role (Literal["user", "assistant"]), content (min_length=1), timestamp (default factory), and metadata fields
- Implemented ConversationState model with scenario_id, variant_id, turns, start_time, and metadata fields
- Implemented add_turn() method that auto-increments turn_number and sets timestamp
- Implemented history property that formats turns as "role: content" separated by newlines
- All models use ConfigDict(extra="ignore") for forward compatibility
- Exported Turn, TurnMetadata, ConversationState from gavel_ai.models package
- Added 38 new unit tests covering all acceptance criteria
- All 920 tests pass (4 pre-existing skips), linting passes

### Senior Developer Review (AI)

**Reviewer:** Claude Opus 4.5 (code-review workflow)
**Date:** 2026-01-18

**Critical Issues Fixed:**
1. Replaced deprecated `datetime.utcnow()` with `datetime.now(UTC)` in models and tests (Python 3.12+ compliance)
2. Removed duplicate timestamp logic in `add_turn()` - now uses Turn's default_factory (DRY principle)

**Review Follow-ups Added:** 3 MEDIUM, 2 LOW (see Tasks section)

### File List

**Files Modified:**
- `src/gavel_ai/models/conversation.py` - Added Turn, TurnMetadata, ConversationState models
- `src/gavel_ai/models/__init__.py` - Exported new models and updated docstring
- `tests/unit/test_conversation.py` - Added 38 new tests for new models

**Files Created:**
_None_

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-18 | Implemented Turn, TurnMetadata, ConversationState models with full test coverage | Claude Opus 4.5 |
| 2026-01-18 | Code review: Fixed deprecated datetime.utcnow(), removed DRY violation, added 5 follow-up items | Claude Opus 4.5 |
