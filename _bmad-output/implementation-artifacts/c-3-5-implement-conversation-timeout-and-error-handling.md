# Story C-3-5: Implement Conversation Timeout and Error Handling

**Status:** ready-for-dev

## Story

As a developer,
I want conversations to timeout and handle errors gracefully,
So that long conversations don't hang and errors are clearly reported.

## Acceptance Criteria

1. **Timeout Enforcement**
   - Given `max_turns` or `max_duration` configured
     When conversation executes
     Then loop terminates when limits reached

2. **TurnGenerator Error Handling**
   - Given TurnGenerator fails (returns error)
     When handled
     Then error logged; conversation marked incomplete; next scenario × variant proceeds

3. **LLM Call Retry Logic**
   - Given LLM call times out
     When error caught
     Then retry logic applied (configurable max_retries); if all fail, mark conversation failed

4. **Results Tracking on Error**
   - Given conversation fails
     When results_raw created
     Then error field populated with error message; execution continues

## Tasks / Subtasks

- [ ] Task 1: Implement Max Turns Limit (AC: #1)
  - [ ] Load max_turns from eval_config.conversational
  - [ ] Track turn_number in conversation loop
  - [ ] Break loop when turn_number >= max_turns
  - [ ] Log: "Conversation reached max_turns limit"

- [ ] Task 2: Implement Max Duration Limit (AC: #1)
  - [ ] Load max_duration_ms from eval_config.conversational (default: 5 minutes)
  - [ ] Track start_time when conversation begins
  - [ ] Check elapsed_time in each loop iteration
  - [ ] Break loop when elapsed_time >= max_duration_ms
  - [ ] Log: "Conversation timeout reached {elapsed_ms}ms"

- [ ] Task 3: Wrap TurnGenerator with Error Handling (AC: #2)
  - [ ] Wrap turn_generator.generate_turn() in try/except
  - [ ] Catch exceptions: network errors, parsing errors, LLM errors
  - [ ] Log error with context: scenario_id, variant_id, turn_number
  - [ ] Set should_continue=False to end conversation
  - [ ] Create error results_raw entry with error field populated
  - [ ] Continue to next scenario × variant

- [ ] Task 4: Implement LLM Call Retry Logic (AC: #3)
  - [ ] Wrap executor.run() LLM calls in retry wrapper (asyncio-retry or similar)
  - [ ] Classify errors:
    - [ ] Transient (timeout, rate limit, temporary service error) → Retry
    - [ ] Permanent (auth failure, invalid request, 4xx errors) → Fail immediately
  - [ ] Configure max_retries (default: 3)
  - [ ] Exponential backoff: 1s, 2s, 4s, 8s (with jitter)
  - [ ] Log retry attempts: "Retrying LLM call {attempt}/{max_retries}"

- [ ] Task 5: Track Errors in Results (AC: #4)
  - [ ] For failed turns, create results_raw entry with:
    - [ ] error: str (error message)
    - [ ] error_type: str (timeout, network, parsing, etc.)
    - [ ] processor_output: null or partial output if available
  - [ ] Maintain conversation transcript even with failed turns
  - [ ] Continue execution to collect as much data as possible

- [ ] Task 6: Add Telemetry for Errors (AC: #2, #3)
  - [ ] Emit OT span: "conversation.error"
  - [ ] Include: error_type, scenario_id, variant_id, turn_number
  - [ ] Track: retry_count (if applicable), total_duration_ms
  - [ ] Set span status to ERROR for failures

- [ ] Task 7: Integration Tests (AC: #1, #2, #3, #4)
  - [ ] Test max_turns enforcement: conversation stops at limit
  - [ ] Test max_duration enforcement: conversation times out
  - [ ] Test TurnGenerator failure handling: conversation marked failed, next scenario proceeds
  - [ ] Test LLM call timeout with retry: eventual success after retries
  - [ ] Test LLM call permanent failure: immediate failure, no retries
  - [ ] Verify error entries in results_raw
  - [ ] Verify error telemetry spans emitted

## Dev Notes

### Error Classification Strategy

```python
def classify_error(error: Exception) -> tuple[str, bool]:
    """
    Classify error as transient or permanent.

    Returns:
        (error_type: str, is_transient: bool)
    """
    error_type = type(error).__name__

    if isinstance(error, asyncio.TimeoutError):
        return ("timeout", True)
    elif isinstance(error, RateLimitError):
        return ("rate_limit", True)
    elif "temporarily unavailable" in str(error).lower():
        return ("service_temporarily_unavailable", True)
    elif isinstance(error, (AuthError, ValueError)):
        return ("permanent", False)
    elif isinstance(error, Exception):
        # Default to transient for unknown errors (safer)
        return ("unknown", True)
```

### Retry Implementation

```python
async def call_with_retry(
    func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
):
    """Call function with exponential backoff retry."""
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            error_type, is_transient = classify_error(e)

            if not is_transient or attempt >= max_retries:
                raise

            delay = min(
                initial_delay * (backoff_factor ** attempt) + random.random(),
                max_delay
            )
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed ({error_type}), "
                f"retrying in {delay:.1f}s: {str(e)}"
            )
            last_error = e
            await asyncio.sleep(delay)
```

### Conversation Loop with Timeouts

```python
async def _execute_conversation(self, scenario, variant, max_turns=10, max_duration_ms=300000):
    """Execute conversation with timeout and error handling."""
    conversation = ConversationState(scenario.id, variant.id)
    results_raw = []
    start_time = datetime.now()

    try:
        turn_generator = TurnGenerator(scenario, variant.model)
        turn_number = 0
        should_continue = True

        while should_continue and turn_number < max_turns:
            # Check duration timeout
            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
            if elapsed_ms >= max_duration_ms:
                logger.warning(f"Conversation timeout: {elapsed_ms}ms >= {max_duration_ms}ms")
                break

            # Generate turn with error handling
            try:
                user_turn = await call_with_retry(
                    lambda: turn_generator.generate_turn(scenario, conversation.history),
                    max_retries=3
                )
            except Exception as e:
                logger.error(f"TurnGenerator failed: {e}")
                results_raw.append({
                    "scenario_id": scenario.id,
                    "variant_id": variant.id,
                    "turn_number": turn_number,
                    "processor_output": None,
                    "error": str(e),
                    "error_type": "turn_generation",
                    "timestamp": datetime.now(timezone.utc)
                })
                break

            conversation.add_turn("user", user_turn.content)

            # LLM call with retry
            try:
                assistant_response = await call_with_retry(
                    lambda: executor.run(variant.prompt, user_turn.content),
                    max_retries=3
                )
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                results_raw.append({
                    "scenario_id": scenario.id,
                    "variant_id": variant.id,
                    "turn_number": turn_number,
                    "processor_output": None,
                    "error": str(e),
                    "error_type": "llm_call",
                    "timestamp": datetime.now(timezone.utc)
                })
                break

            conversation.add_turn("assistant", assistant_response)
            results_raw.append({
                "scenario_id": scenario.id,
                "variant_id": variant.id,
                "turn_number": turn_number,
                "processor_output": assistant_response,
                "error": None,
                "timestamp": datetime.now(timezone.utc)
            })

            should_continue = user_turn.should_continue
            turn_number += 1

        return ConversationResult(
            scenario_id=scenario.id,
            variant_id=variant.id,
            conversation_transcript=conversation,
            results_raw=results_raw,
            duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
        )

    except Exception as e:
        logger.error(f"Conversation execution failed catastrophically: {e}")
        # Return partial result with error
        return ConversationResult(
            scenario_id=scenario.id,
            variant_id=variant.id,
            conversation_transcript=conversation,
            results_raw=results_raw,
            error=str(e),
            duration_ms=int((datetime.now() - start_time).total_seconds() * 1000)
        )
```

### Configuration

**eval_config.json:**
```json
{
  "conversational": {
    "max_turns": 10,
    "max_duration_ms": 300000,
    "max_turn_length": 2000,
    "turn_generator": {
      "model": "claude-3-5-sonnet",
      "temperature": 0,
      "max_tokens": 500
    },
    "error_handling": "collect_all",
    "retry_config": {
      "max_retries": 3,
      "initial_delay_ms": 1000,
      "max_delay_ms": 30000,
      "backoff_factor": 2.0
    }
  }
}
```

### Error Types to Track

| Error Type | Cause | Transient? | Action |
|-----------|-------|-----------|--------|
| timeout | LLM call exceeded timeout | Yes | Retry with backoff |
| rate_limit | API rate limit exceeded | Yes | Retry with backoff |
| auth_error | Invalid API key or credentials | No | Fail immediately |
| network_error | Connection failure | Yes | Retry with backoff |
| parsing_error | Failed to parse LLM response | No | Fail, mark turn incomplete |
| turn_generation | TurnGenerator failed | No | End conversation |
| service_unavailable | API service temporarily down | Yes | Retry with backoff |

### References

- Conversational Epic Architecture: `_bmad-output/planning-artifacts/epics-conversational-eval.md#story-c35`
- Error Handling: `_bmad-output/planning-artifacts/tdd-conversational-eval.md#error-handling`
- Retry Pattern: `src/gavel_ai/core/execution/retry_logic.py` (Story 3.7)
- Telemetry: `src/gavel_ai/telemetry/__init__.py`

## Dev Agent Record

### Agent Model Used

Claude 3.5 Sonnet (via BMAD create-story workflow)

### Debug Log References

None yet - story not started

### Completion Notes List

- [ ] Max turns limit implemented and tested
- [ ] Max duration limit implemented and tested
- [ ] TurnGenerator error handling working correctly
- [ ] LLM call retry logic implemented with exponential backoff
- [ ] Error classification (transient vs permanent) implemented
- [ ] Error fields in results_raw populated correctly
- [ ] Conversation continues gracefully on errors
- [ ] Telemetry spans for errors emitted
- [ ] Integration tests covering all error scenarios
- [ ] All acceptance criteria verified
- [ ] Code review completed

### File List

- `src/gavel_ai/conversational/steps/processing_step.py` (main implementation)
- `src/gavel_ai/core/execution/retry_logic.py` (retry utilities)
- `src/gavel_ai/conversational/errors.py` (error types and classification)
- `tests/integration/test_conversation_timeout_error.py` (integration tests)
