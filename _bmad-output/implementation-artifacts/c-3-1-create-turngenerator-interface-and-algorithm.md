# Story C-3-1: Create TurnGenerator Interface and Algorithm

**Status:** done

## Story

As a developer,
I want a TurnGenerator component that creates turns dynamically,
So that conversations adapt to LLM responses in real-time.

## Acceptance Criteria

1. **TurnGenerator Interface Definition**
   - Given TurnGenerator is initialized with a scenario and LLM model
     When examined
     Then it has: `async generate_turn(scenario, history) → GeneratedTurn`

2. **Deterministic Turn Generation**
   - Given same scenario and history are provided twice with temperature=0
     When `generate_turn()` called
     Then identical turns are generated (deterministic)

3. **Context-Aware Turn Generation**
   - Given conversation history is provided
     When turn generated
     Then next turn moves toward scenario.user_goal and respects dialogue_guidance

4. **Conversation Flow Control**
   - Given user_goal is achieved or max_turns reached
     When should_continue evaluated
     Then it's set to False to end conversation

5. **Return Type Structure**
   - Given `generate_turn()` completes
     When result examined
     Then it returns: `{content (str), metadata (dict), should_continue (bool)}`

## Tasks / Subtasks

- [x] Task 1: Define TurnGenerator ABC with interface (AC: #1)
  - [x] Create `src/gavel_ai/processors/turn_generator.py` (located in processors per existing codebase pattern)
  - [x] Define TurnGenerator class with async generate_turn method signature
  - [x] Define GeneratedTurn Pydantic model
  - [x] Add docstrings with clear contracts

- [x] Task 2: Implement LLMBasedTurnGenerator (AC: #2, #3)
  - [x] Implement TurnGenerator as concrete implementation (no ABC needed for single impl)
  - [x] Wire provider factory for LLM agent creation
  - [x] Implement prompt rendering with scenario + history context
  - [x] Add temperature=0 for deterministic generation (configurable)
  - [x] Extract should_continue logic based on goal/max_turns

- [x] Task 3: Add Goal Detection (AC: #4)
  - [x] Implement goal detection based on keyword analysis with negation avoidance
  - [x] Configure goal achievement threshold/keywords
  - [x] Ensure max_turns hard limit

- [x] Task 4: Add Telemetry (AC: #2, #3)
  - [x] Emit OT spans: "generate_turn"
  - [x] Include attributes: scenario_id, total_turns, should_continue, deterministic_mode
  - [x] Measure generation latency (generation_time_ms)

- [x] Task 5: Unit Tests (AC: #2, #3, #4)
  - [x] Test determinism: same inputs → same output with temperature=0
  - [x] Test goal detection: various goal states (thank you, thanks, perfect, worked, resolved)
  - [x] Test max_turns boundary: should_continue=False after max_turns
  - [x] Test edge cases: empty history, very long history
  - [x] Mock LLM provider for reliable tests (30 tests total)

## Dev Notes

### Architecture Patterns

**TurnGenerator Location:** `src/gavel_ai/processors/turn_generator.py` (concrete class, not ABC)

```python
from pydantic import BaseModel, Field
from typing import Any, Dict

class GeneratedTurn(BaseModel):
    """Data structure for a generated turn in conversation."""
    
    content: str = Field(..., description="Content of generated turn")
    metadata: Dict[str, Any] = Field(..., description="Metadata about turn generation")
    should_continue: bool = Field(..., description="Whether conversation should continue")

class TurnGenerator:
    """Component that creates turns dynamically for conversational evaluation."""
    
    async def generate_turn(
        self,
        scenario: "ConversationScenario",
        history: "ConversationState",
    ) -> GeneratedTurn:
        """Generate next user turn based on scenario and conversation history."""
        # Implementation uses inline prompt builder and goal detection
        pass
```

**LLMBasedTurnGenerator Responsibilities:**
- Load turn generation prompt template
- Render with scenario context (user_goal, context, dialogue_guidance)
- Render with conversation history
- Call LLM via ProviderFactory with temperature=0
- Parse LLM response to extract turn content
- Analyze response for goal achievement signals
- Determine should_continue based on:
  - Goal achievement (detected via LLM analysis or keywords)
  - Max turns reached (current_turn_number >= max_turns)
  - Conversation natural endpoint (LLM says "END_CONVERSATION")

**Data Model Alignment:**
- Uses existing ConversationScenario model from C-1.1
- Returns GeneratedTurn which ConversationalProcessingStep consumes
- Integrates with ProviderFactory from oneshot execution pipeline

**Determinism Strategy:**
- temperature=0 in LLM config for reproducible generation
- Same scenario + history → identical turn content
- Randomness eliminated via seeding if provider supports it

### Considerations

- **Performance:** Turn generation <1s per turn (NFR-C-P1)
- **Telemetry:** Capture generation timing for observability
- **Provider Integration:** Reuse ProviderFactory from existing codebase (Story 3.6 pattern)
- **Error Handling:** Graceful degradation if LLM fails; log error and mark should_continue=False

### Integration Points

- **Consumed by:** ConversationalProcessingStep (C-3.2)
- **Uses:** ProviderFactory from `src/gavel_ai/providers/factory.py`
- **Uses:** ConversationScenario from `src/gavel_ai/models/conversation.py`
- **Uses:** Telemetry get_tracer() from `src/gavel_ai/telemetry/__init__.py`

### References

- Conversational Epic Architecture: `_bmad-output/planning-artifacts/epics-conversational-eval.md#epic-c3`
- Turn Generation Spec: `_bmad-output/planning-artifacts/tdd-conversational-eval.md#turn-generation`
- Provider Factory Pattern: `src/gavel_ai/core/providers/factory.py` (Story 3.6)
- Telemetry Integration: `src/gavel_ai/telemetry/__init__.py`

## Dev Agent Record

### Agent Model Used

Claude 3.5 Sonnet (via BMAD create-story workflow)

### Debug Log References

**Implementation Phase:**
- Fixed syntax errors in pre-existing turn_generator.py (orphaned code block at lines 98-102)
- Fixed syntax errors in pre-existing conversation.py (malformed try/except in JSONL parser)
- Added iter_conversation_scenarios() function that was exported but missing
- Updated test assertion for error message wording change

**Code Review Phase (2026-01-19):**
- Fixed HIGH severity: Committed test_turn_generator.py to git (was untracked)
- Fixed MEDIUM severity: Added ProcessorError handling in TurnGenerator.__init__
- Fixed MEDIUM severity: Corrected ProviderFactory path in Dev Notes (core/providers → providers)
- Fixed MEDIUM severity: Corrected ConversationScenario location in Dev Notes (conversational/config → models/conversation)
- Fixed LOW severity: Updated outdated ABC code example to reflect concrete class implementation

### Completion Notes List

- [x] TurnGenerator class defined and documented with async generate_turn method
- [x] LLMBasedTurnGenerator implemented as TurnGenerator with deterministic generation
- [x] Goal detection implemented using keyword matching with negation avoidance
- [x] Unit tests: 30 tests covering all acceptance criteria
- [x] Integration with ProviderFactory verified
- [x] Telemetry spans emitted correctly with required attributes
- [x] All acceptance criteria verified
- [x] Code review completed and fixes applied

### Implementation Notes

**Architecture Deviation:** The story spec suggested `src/gavel_ai/conversational/turn_generator.py` but the existing codebase structure placed it at `src/gavel_ai/processors/turn_generator.py`. This follows the established pattern where processor-like components live in `processors/`.

**No Prompt Template:** The story mentioned a TOML prompt template file, but the implementation uses an inline prompt builder (`_build_turn_prompt`) which is more maintainable for this use case.

**No ABC Pattern:** The implementation uses a concrete TurnGenerator class rather than an ABC + LLMBasedTurnGenerator pattern since there's only one implementation strategy currently needed.

### File List

- `src/gavel_ai/processors/turn_generator.py` (main implementation - fixed syntax errors, cleaned up)
- `src/gavel_ai/models/conversation.py` (fixed syntax errors, added iter_conversation_scenarios)
- `tests/unit/test_turn_generator.py` (unit tests - 30 comprehensive tests)
- `tests/unit/test_conversation.py` (updated error message assertion)

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-19 | Fixed syntax errors in turn_generator.py and conversation.py; Added 30 unit tests; Story complete and ready for review | Dev Agent (Claude) |
| 2026-01-19 | Code review: Committed test file to git; Added error handling in __init__; Fixed Dev Notes paths | Senior Developer Review (AI) |
