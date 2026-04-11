# Story C4.2: integrate-turn-judges-into-orchestration

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Developer,
I want turn judges (DeepEval, GEval, bespoke) to be applied to conversations,
so that turn-level scoring is supported.

## Acceptance Criteria

1. **Given** turn judges configured in `eval_config.json`, **When** executed, **Then** each turn judge receives the entire conversation and produces an aggregate score or turn-by-turn scores.
2. **Given** turn judge types: DeepEval (out-of-box), GEval (manual config), Bespoke (custom), **When** applied, **Then** each type executes via the unified `Judge` interface.
3. **Given** multiple turn judges of different types, **When** applied to one conversation, **Then** all turn judges execute and all results are collected.
4. **Given** a turn judge execution, **When** completed, **Then** the result includes the `turn_number` it applies to (or indicates it's an aggregate if applicable).

## Tasks / Subtasks

- [ ] Implement `TurnJudge` logic within `DeepEvalJudge` (AC: 1, 2)
  - [ ] Adapt DeepEval turn-level metrics (e.g., `relevancy`, `faithfulness` applied to turns)
- [ ] Implement `TurnJudge` logic for `GEvalJudge` (AC: 1, 2)
  - [ ] Allow GEval to target specific turns or the whole conversation context for a turn's score
- [ ] Ensure `BespokeJudge` can correctly identify itself as a `turn` judge (AC: 2)
- [ ] Update `JudgeExecutor` to handle batching of turn-level evaluations (AC: 3)
- [ ] Add unit tests for turn-level judging across all three judge classes (AC: 4)

## Dev Notes

- **Turn vs. Conversation:** Turn judges evaluate individual assistant responses. However, because each response depends on history, the `Judge` receives the full `ConversationResult`.
- **DeepEval Mapping:** Many DeepEval metrics can be applied turn-by-turn. We need to ensure the `LLMTestCase` passed to DeepEval is correctly constructed for each turn.
- **Reference:** [Source: _bmad-output/planning-artifacts/tdd-conversational-eval.md#3.1 Turn-Level Judging]

### Project Structure Notes

- Touch `src/gavel_ai/judges/deepeval_judge.py`
- Touch `src/gavel_ai/judges/geval_judge.py`
- Touch `src/gavel_ai/judges/bespoke_judge.py`
- Touch `src/gavel_ai/judges/judge_executor.py`

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

- src/gavel_ai/judges/deepeval_judge.py
- src/gavel_ai/judges/geval_judge.py
- src/gavel_ai/judges/bespoke_judge.py
- src/gavel_ai/judges/judge_executor.py
- tests/unit/judges/test_turn_judging.py
