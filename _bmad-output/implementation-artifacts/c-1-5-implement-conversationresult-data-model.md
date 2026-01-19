# Story C1.5: Implement ConversationResult Data Model

Status: done

## Story

As a developer,
I want ConversationResult to capture execution outcome,
So that results can be stored and passed to judge runner.

## Acceptance Criteria

1. **Given** ConversationResult is created
   **When** examined
   **Then** it has: scenario_id, variant_id, conversation_transcript (ConversationState), results_raw (list), duration_ms, tokens_total

2. **Given** ConversationResult is created with results_raw
   **When** examined
   **Then** each entry contains: processor_output, timing_ms, tokens_prompt, tokens_completion, error (optional)

3. **Given** multiple conversations are executed
   **When** results are aggregated
   **Then** each ConversationResult is independent and complete

4. **Given** ConversationResult is serialized
   **When** written to conversations.jsonl
   **Then** full transcript and metadata are preserved

**Related Requirements:** FR-C2.3, FR-C6.2

## Tasks / Subtasks

- [x] Task 1: Create TurnResult nested model (AC: #2)
  - [x] 1.1: Define `TurnResult` model in `src/gavel_ai/models/conversation.py`
  - [x] 1.2: Add `turn_number: int` field
  - [x] 1.3: Add `processor_output: str` field (assistant response)
  - [x] 1.4: Add `timing_ms: int` field (latency for this turn)
  - [x] 1.5: Add `tokens_prompt: Optional[int]` field
  - [x] 1.6: Add `tokens_completion: Optional[int]` field
  - [x] 1.7: Add `error: Optional[str]` field for turn-level errors

- [x] Task 2: Create ConversationResult Pydantic model (AC: #1, #3)
  - [x] 2.1: Define `ConversationResult` model in `src/gavel_ai/models/conversation.py`
  - [x] 2.2: Add `scenario_id: str` field (required)
  - [x] 2.3: Add `variant_id: str` field (required)
  - [x] 2.4: Add `conversation_transcript: ConversationState` field (full dialogue)
  - [x] 2.5: Add `results_raw: List[TurnResult]` field (per-turn processor results)
  - [x] 2.6: Add `duration_ms: int` field (total conversation duration)
  - [x] 2.7: Add `tokens_total: int` field (sum of all tokens)
  - [x] 2.8: Add `completed: bool` field (whether goal achieved or max_turns reached)
  - [x] 2.9: Add `error: Optional[str]` field for conversation-level errors

- [x] Task 3: Implement helper methods on ConversationResult (AC: #1, #3)
  - [x] 3.1: Implement `total_turns` property returning len(conversation_transcript.turns)
  - [x] 3.2: Implement `compute_tokens_total() -> int` method summing all turn tokens
  - [x] 3.3: Implement `to_jsonl_entry() -> dict` method for JSONL serialization

- [x] Task 4: Implement serialization for conversations.jsonl (AC: #4)
  - [x] 4.1: Ensure ConversationState can serialize nested Turns properly
  - [x] 4.2: Add `model_dump(mode='json')` support for datetime serialization
  - [x] 4.3: Verify round-trip: serialize to JSON, deserialize back to ConversationResult

- [x] Task 5: Export models from gavel_ai.models package (AC: #1)
  - [x] 5.1: Update `src/gavel_ai/models/__init__.py` to export ConversationResult, TurnResult
  - [x] 5.2: Add to `__all__` list for clean imports

- [x] Task 6: Write unit tests (AC: #1, #2, #3, #4)
  - [x] 6.1: Add tests in `tests/unit/test_conversation.py` for new models
  - [x] 6.2: Test ConversationResult with all fields populated
  - [x] 6.3: Test ConversationResult with nested ConversationState and Turns
  - [x] 6.4: Test TurnResult with all fields including error
  - [x] 6.5: Test total_turns property
  - [x] 6.6: Test compute_tokens_total method
  - [x] 6.7: Test to_jsonl_entry serialization
  - [x] 6.8: Test JSON round-trip (serialize then deserialize)
  - [x] 6.9: Test multiple independent ConversationResults

### Review Follow-ups (AI)
- [x] [AI-Review][Medium] Validate `tokens_total` matches `results_raw` sum or remove field in favor of property [src/gavel_ai/models/conversation.py]
- [x] [AI-Review][Medium] Rename `TurnResult.timing_ms` to `latency_ms` to match `TurnMetadata` [src/gavel_ai/models/conversation.py]
- [x] [AI-Review][Medium] Optimize `to_jsonl_entry` serialization to exclude None values [src/gavel_ai/models/conversation.py]
- [x] [AI-Review][Low] Document extensibility pattern for `TurnResult` extra fields [src/gavel_ai/models/conversation.py]
- [x] [AI-Review][Low] Clarify `completed` vs `error` relationship in docstrings or validation [src/gavel_ai/models/conversation.py]

## Dev Notes

### Architecture Patterns & Constraints

**Model Location:** `src/gavel_ai/models/conversation.py` - Add to existing conversational models module.

**DEPENDENCY:** This story depends on C1.3 (Turn and ConversationState models). Ensure those are implemented first.

**Pydantic Configuration (MANDATORY):**
```python
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


class TurnResult(BaseModel):
    """Result of processing a single conversation turn."""
    model_config = ConfigDict(extra='ignore')

    turn_number: int = Field(
        ...,
        ge=0,
        description="Turn number this result corresponds to"
    )
    processor_output: str = Field(
        ...,
        description="Assistant response (processor output)"
    )
    timing_ms: int = Field(
        ...,
        ge=0,
        description="Processing time in milliseconds"
    )
    tokens_prompt: Optional[int] = Field(
        None,
        description="Number of prompt tokens"
    )
    tokens_completion: Optional[int] = Field(
        None,
        description="Number of completion tokens"
    )
    error: Optional[str] = Field(
        None,
        description="Error message if turn processing failed"
    )


class ConversationResult(BaseModel):
    """Complete result of a conversational evaluation execution."""
    model_config = ConfigDict(extra='ignore')

    scenario_id: str = Field(
        ...,
        description="ID of the scenario that was executed"
    )
    variant_id: str = Field(
        ...,
        description="ID of the variant (model/config) used"
    )
    conversation_transcript: ConversationState = Field(
        ...,
        description="Full conversation transcript with all turns"
    )
    results_raw: List[TurnResult] = Field(
        default_factory=list,
        description="Per-turn processor results"
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Total conversation duration in milliseconds"
    )
    tokens_total: int = Field(
        0,
        ge=0,
        description="Total tokens used across all turns"
    )
    completed: bool = Field(
        False,
        description="Whether conversation completed successfully (goal achieved or max_turns)"
    )
    error: Optional[str] = Field(
        None,
        description="Conversation-level error if execution failed"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this result was created"
    )

    @computed_field
    @property
    def total_turns(self) -> int:
        """Total number of turns in the conversation."""
        return len(self.conversation_transcript.turns)

    def compute_tokens_total(self) -> int:
        """Compute total tokens from all turn results."""
        total = 0
        for result in self.results_raw:
            if result.tokens_prompt:
                total += result.tokens_prompt
            if result.tokens_completion:
                total += result.tokens_completion
        return total

    def to_jsonl_entry(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for JSONL serialization.

        Returns:
            Dict ready for json.dumps() with ISO format datetimes
        """
        return self.model_dump(mode='json')
```

### Example ConversationResult

```python
# Create conversation state with turns
state = ConversationState(
    scenario_id="booking_flight",
    variant_id="claude-3.5-sonnet"
)
state.add_turn("user", "I want to book a flight to NYC")
state.add_turn("assistant", "I'd be happy to help. What dates?")

# Create turn results
turn_results = [
    TurnResult(
        turn_number=0,
        processor_output="I'd be happy to help. What dates?",
        timing_ms=1250,
        tokens_prompt=45,
        tokens_completion=12
    )
]

# Create conversation result
result = ConversationResult(
    scenario_id="booking_flight",
    variant_id="claude-3.5-sonnet",
    conversation_transcript=state,
    results_raw=turn_results,
    duration_ms=2500,
    tokens_total=57,
    completed=False  # conversation not yet complete
)

# Serialize for JSONL
jsonl_entry = result.to_jsonl_entry()
# Write to file: json.dumps(jsonl_entry)
```

### conversations.jsonl Format

Each line in `conversations.jsonl` is a complete ConversationResult:

```json
{"scenario_id": "booking_flight", "variant_id": "claude-3.5-sonnet", "conversation_transcript": {"scenario_id": "booking_flight", "variant_id": "claude-3.5-sonnet", "turns": [{"turn_number": 0, "role": "user", "content": "I want to book a flight", "timestamp": "2026-01-18T10:00:00Z"}, {"turn_number": 1, "role": "assistant", "content": "I'd be happy to help", "timestamp": "2026-01-18T10:00:01Z"}], "start_time": "2026-01-18T10:00:00Z"}, "results_raw": [{"turn_number": 0, "processor_output": "I'd be happy to help", "timing_ms": 1250, "tokens_prompt": 45, "tokens_completion": 12}], "duration_ms": 2500, "tokens_total": 57, "completed": false, "timestamp": "2026-01-18T10:00:02Z"}
```

### Testing Standards

- Tests go in existing `tests/unit/test_conversation.py`
- Use pytest fixtures from `conftest.py`
- Test all computed fields (total_turns, compute_tokens_total)
- Test serialization round-trip
- Target >90% coverage on new models

### References

- [Source: _bmad-output/planning-artifacts/epics-conversational-eval.md#Story C1.5]
- [Source: _bmad-output/planning-artifacts/project-context.md#Type Hints & Validation]
- [Pattern: src/gavel_ai/models/runtime.py - OutputRecord, ProcessorResult patterns]
- [Dependency: C1.3 - Turn and ConversationState models]

## Dev Agent Record

### Agent Model Used

Antigravity (Google DeepMind)

### Debug Log References

- ImportError 'ConversationState' during initial testing (fixed by imports in __init__.py and proper definition order awareness)
- Syntax issue with append needing newline handled.

### Completion Notes List

### Completion Notes List

- Implemented `TurnResult` with extensive validation fields
- Implemented `ConversationResult` with helper methods (`compute_tokens_total`, `total_turns`)
- Exported models in `gavel_ai.models`
- Added comprehensive unit tests in `tests/unit/test_conversation.py` achieving 100% pass rate
- Verified JSONL serialization compatibility

### File List

### File List

**Files to Modify:**
- `src/gavel_ai/models/conversation.py` - Add TurnResult, ConversationResult models
- `src/gavel_ai/models/__init__.py` - Export new models
- `tests/unit/test_conversation.py` - Add tests for new models

**Files Created:**
_None_
