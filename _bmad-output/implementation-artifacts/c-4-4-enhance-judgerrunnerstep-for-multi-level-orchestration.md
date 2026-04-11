# Story C4.4: enhance-judgerrunnerstep-for-multi-level-orchestration

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Developer,
I want JudgeRunnerStep to orchestrate all judge types and produce flattened JSONL output,
so that complete multi-level judging is available.

## Acceptance Criteria

1. **Given** `JudgeRunnerStep` receives conversational results (`conversations.jsonl`, `results_raw.jsonl`), **When** executed, **Then** it applies all configured judges (turn + conversation) to each conversation.
2. **Given** judges complete, **When** results collected, **Then** `results_judged.jsonl` is created with one entry per (scenario × variant × judge) combo.
3. **Given** `results_judged.jsonl` examined, **When** checked, **Then** each line is an independent JSONL entry with: `scenario_id`, `variant_id`, `judge_id`, `judge_score`, `judge_reasoning`, `judge_evidence`.
4. **Given** a conversational run, **When** judging completes, **Then** `results_judged.jsonl` contains both turn-level and conversation-level judge results in a flattened format.

## Tasks / Subtasks

- [ ] Update `JudgeRunnerStep.execute` to detect conversational runs (AC: 1)
  - [ ] Load `conversations.jsonl` and `results_raw.jsonl` from context/disk
- [ ] Orchestrate judge execution across multiple levels (AC: 1)
  - [ ] Execute turn-level judges for each turn
  - [ ] Execute conversation-level judges for each full transcript
- [ ] Implement result flattening logic (AC: 2, 4)
  - [ ] Map complex multi-level results into the standard `results_judged.jsonl` schema
- [ ] Ensure `results_judged.jsonl` is written correctly with accurate metadata (AC: 3)
- [ ] Add integration tests for the full judging orchestration flow (AC: 1-4)

## Dev Notes

- **OneShot Compatibility:** Ensure `JudgeRunnerStep` still works perfectly for OneShot evaluations.
- **Flattened Schema:** Stick to the "Decision 4: Flat run artifact schema" from the main architecture. Every judge result, whether for a turn or a whole conversation, should be its own entry or part of a flattened record.
- **Reference:** [Source: _bmad-output/planning-artifacts/tdd-conversational-eval.md#3.4 Flattened Judge Output Schema]

### Project Structure Notes

- Touch `src/gavel_ai/core/steps/judge_runner.py`
- Touch `src/gavel_ai/core/result_storage.py` (if needed for JSONL flattening)

### References

- [_bmad-output/planning-artifacts/epics-conversational-eval.md](_bmad-output/planning-artifacts/epics-conversational-eval.md)
- [_bmad-output/planning-artifacts/tdd-conversational-eval.md](_bmad-output/planning-artifacts/tdd-conversational-eval.md)

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 2.0 Flash Thinking)

### Debug Log References

None

### Completion Notes List

None

### File List

- src/gavel_ai/core/steps/judge_runner.py
- src/gavel_ai/core/result_storage.py
- tests/integration/test_judge_orchestration.py
