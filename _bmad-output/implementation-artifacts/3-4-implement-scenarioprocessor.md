# Story 3.4: Implement ScenarioProcessor

Status: done

## Story

As a user,
I want to evaluate multi-turn conversational scenarios,
So that I can test context-aware dialogue systems.

## Acceptance Criteria

1. **Multi-Turn Processing:**
   - Given ScenarioProcessor wraps another InputProcessor
   - When process() is called with multiple inputs (turns)
   - Then each turn is processed sequentially with accumulated context

2. **Context Accumulation:**
   - Given previous turns have been processed
   - When processing a new turn
   - Then conversation_history is added to input metadata

3. **Metadata Aggregation:**
   - Given multiple turns produce metadata
   - When the scenario completes
   - Then metadata is aggregated (totals summed, per-turn preserved)

## Tasks / Subtasks

- [x] Task 1: Create ScenarioProcessor class
  - [x] Inherit from InputProcessor ABC
  - [x] Accept inner_processor in constructor
  - [x] Set up conversation history tracking

- [x] Task 2: Implement multi-turn processing
  - [x] Iterate through input turns sequentially
  - [x] Add conversation_history to each turn's metadata
  - [x] Call inner_processor for each turn
  - [x] Accumulate outputs across turns

- [x] Task 3: Implement metadata aggregation
  - [x] Sum total_* metadata fields
  - [x] Preserve per-turn metadata with turn_N_ prefix
  - [x] Combine outputs with turn labels

- [x] Task 4: Update module exports
  - [x] Export ScenarioProcessor from processors/__init__.py

## Dev Agent Record

### Agent Model Used
Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### Completion Notes
- ✅ Created ScenarioProcessor (83 lines)
- ✅ Multi-turn conversation context management
- ✅ Metadata aggregation across turns
- ✅ Telemetry spans with turn tracking
- ✅ Updated processors/__init__.py exports

### File List

**New Files:**
- `src/gavel_ai/processors/scenario_processor.py` (83 lines)

**Modified Files:**
- `src/gavel_ai/processors/__init__.py`

## Change Log

- **2025-12-29**: ✅ Implementation complete - All ACs satisfied
