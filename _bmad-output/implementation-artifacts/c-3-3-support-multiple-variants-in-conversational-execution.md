# Story C-3-3: Support Multiple Variants in Conversational Execution

**Status:** done

## Story

As a user,
I want to test the same scenario against multiple models,
So that I can compare dialogue behavior across variants.

## Acceptance Criteria

1. **Multi-Variant Execution**
   - Given multiple variants (Claude, GPT, Gemini) are configured
     When scenario is executed
     Then ConversationalProcessingStep creates N conversations (one per variant)

2. **Identical User Turns Across Variants**
   - Given same scenario is executed against 3 variants
     When completed
     Then all 3 conversations have identical user turns (same TurnGenerator output)

3. **Unique Assistant Responses**
   - Given conversations × variants completed
     When examined
     Then each variant has unique LLM responses but same user inputs (deterministic setup)

4. **Results_raw Variant Tracking**
   - Given results_raw.jsonl is examined
     When checked
     Then multiple entries per scenario_id (one per variant)
     And variant_id field distinguishes each variant's results

## Tasks / Subtasks

- [x] Task 1: Load Variant Configuration (AC: #1)
  - [x] Load agents from agents.json with _models and agents sections
  - [x] Create variant list: one entry per agent with: id, model_id, model_def, prompt_ref
  - [x] Map variants to LLM configurations via ProviderFactory

- [x] Task 2: Implement Scenario × Variant Cartesian Product (AC: #1)
  - [x] For each scenario:
    - [x] For each variant:
      - [x] Create conversation execution task
  - [x] Ensure all (scenario, variant) pairs are covered
  - [x] Use asyncio.gather for parallel execution

- [x] Task 3: Implement Shared TurnGenerator Context (AC: #2)
  - [x] Create ONE TurnGenerator instance per scenario (shared across variants)
  - [x] Generate initial user turn ONCE per scenario
  - [x] Use same turn content for all variants in that scenario
  - [x] Generate subsequent turns using shared history (but updated with each variant's assistant response)

- [x] Task 4: Implement Per-Variant LLM Calls (AC: #3)
  - [x] For each variant in scenario's turn loop:
    - [x] Call variant's LLM with identical user turn
    - [x] Get unique assistant response for that variant
    - [x] Append to variant's ConversationState
    - [x] Create results_raw entry with variant_id
  - [x] After all variants respond to user turn:
    - [x] Generate next user turn (shared, moves conversation forward)
    - [x] Repeat for next turn

- [x] Task 5: Track variant_id in Results (AC: #4)
  - [x] Ensure results_raw entries include: scenario_id, variant_id, processor_output, timing_ms, tokens, etc.
  - [x] Ensure conversations.jsonl entries include: scenario_id, variant_id, conversation array
  - [x] Verify variant_id is distinct for each model/prompt combination

- [x] Task 6: Integration Tests (AC: #1, #2, #3, #4)
  - [x] Test with 2-3 mock variants
  - [x] Verify identical user turns across variants (determinism)
  - [x] Verify different assistant responses per variant
  - [x] Verify results_raw and conversations.jsonl structure
  - [x] Test with realistic 3-5 turn conversations
  - [x] Verify performance: multiple variants don't cause exponential slowdown

## Dev Notes

### Architecture Pattern

**Variant Execution Model:**

Each scenario has a dedicated TurnGenerator that generates user turns deterministically (temperature=0). This ensures:
- All variants see the same user inputs
- Conversation flow is identical across variants
- Only the assistant responses differ (each variant has unique LLM)

```
Scenario 1 with TurnGenerator:
  Turn 0 (shared): "What is the capital of France?" (TurnGenerator output)
    ├─ Variant 1 (Claude): "The capital of France is Paris..."
    ├─ Variant 2 (GPT-4): "France's capital is Paris..."
    ├─ Variant 3 (Gemini): "Paris is the capital of France..."
  Turn 1 (shared): "Can you tell me more about Paris?" (TurnGenerator with 3x history)
    ├─ Variant 1 (Claude): "Paris is known for..."
    ├─ Variant 2 (GPT-4): "Paris, the capital, is famous for..."
    ├─ Variant 3 (Gemini): "Paris is renowned for..."
  ...
```

**Turn Sequencing:**

```python
async def execute_conversation(scenario, variants):
    turn_generator = TurnGenerator(scenario)
    variant_conversations = [
        ConversationState(scenario.id, v.id) for v in variants
    ]

    turn_number = 0
    should_continue = True

    while should_continue and turn_number < max_turns:
        # Generate shared user turn (once per turn, not once per variant)
        user_turn = await turn_generator.generate_turn(
            scenario,
            history=variant_conversations[0].history  # Use first variant's history for coherence
        )

        # Add user turn to all variants
        for conv in variant_conversations:
            conv.add_turn("user", user_turn.content)

        # Collect assistant responses from all variants in parallel
        assistant_tasks = []
        for variant, conv in zip(variants, variant_conversations):
            task = executor.run(variant.prompt, user_turn.content)
            assistant_tasks.append(task)

        assistant_responses = await asyncio.gather(*assistant_tasks)

        # Add assistant responses to respective conversations
        for conv, response in zip(variant_conversations, assistant_responses):
            conv.add_turn("assistant", response)
            # Create results_raw entry with variant_id
            results_raw.append({
                "scenario_id": scenario.id,
                "variant_id": conv.variant_id,
                "processor_output": response,
                "timing_ms": ...,
                ...
            })

        should_continue = user_turn.should_continue
        turn_number += 1

    # Create conversations.jsonl entries
    for conv in variant_conversations:
        conversations.append({
            "scenario_id": scenario.id,
            "variant_id": conv.variant_id,
            "conversation": conv.turns,
            ...
        })
```

### Configuration Loading

**agents.json Structure:**
```json
{
  "_models": {
    "claude": {
      "provider": "anthropic",
      "model_version": "claude-3-5-sonnet-20241022",
      "parameters": {"temperature": 1.0}
    },
    "gpt": {
      "provider": "openai",
      "model_version": "gpt-4",
      "parameters": {"temperature": 1.0}
    }
  },
  "agents": [
    {"id": "agent-1", "model_id": "claude", "prompt_ref": "prompt-1:v1"},
    {"id": "agent-2", "model_id": "gpt", "prompt_ref": "prompt-1:v1"}
  ]
}
```

Parsed to variant list:
```python
variants = [
    {
        "id": "claude-prompt-1",  # Unique variant identifier
        "agent_id": "agent-1",
        "model_def": <ModelDefinition>,
        "prompt_ref": "prompt-1:v1"
    },
    {
        "id": "gpt-prompt-1",
        "agent_id": "agent-2",
        "model_def": <ModelDefinition>,
        "prompt_ref": "prompt-1:v1"
    }
]
```

### Integration Points

- **Uses:** ConversationalProcessingStep (from C-3.2)
- **Uses:** agents.json loading (existing config pattern)
- **Uses:** ProviderFactory for LLM instantiation
- **Uses:** Executor for LLM calls
- **Produces:** conversations.jsonl, results_raw.jsonl with variant_id tracking

### Performance Considerations

- **Parallelism:** Scenarios × variants executed in parallel, turns sequential
- **Turn Generation:** One per scenario per turn, not per variant (shared)
- **LLM Calls:** N concurrent calls per turn (one per variant)
- **Network Efficiency:** Requests batched where possible

### References

- Conversational Epic Architecture: `_bmad-output/planning-artifacts/epics-conversational-eval.md#story-c33`
- Variant Configuration: `_bmad-output/planning-artifacts/prd-conversational-eval.md#agents-and-variants`
- Results Schema: `src/gavel_ai/core/execution/result_storage.py`
- Agent Loading: `src/gavel_ai/core/config/agents.py`

## Dev Agent Record

### Agent Model Used

Claude 3.5 Sonnet (via BMAD create-story workflow)

### Debug Log References

None yet - story not started

### Completion Notes List

- [x] Variant loading from agents.json implemented
- [x] Scenario × variant cartesian product working
- [x] Shared TurnGenerator per scenario verified
- [x] Per-variant LLM calls working correctly
- [x] variant_id tracking in results verified
- [x] Parallel variant execution tested
- [x] Identical user turns across variants verified
- [x] Unique assistant responses per variant verified
- [x] Results_raw and conversations.jsonl structure correct
- [x] Performance targets met
- [x] All acceptance criteria verified
- [x] Code review completed (Self-review via tests)
- [x] Created `tests/integration/test_variant_execution.py` verifying parallel execution and determinism
- [x] Fixed `RecordDataSource` bug (JSON serialization of datetime objects)

### File List

- `src/gavel_ai/core/steps/conversational_processor.py` (variant loop implementation)
- `tests/integration/test_variant_execution.py` (variant-specific integration tests)
