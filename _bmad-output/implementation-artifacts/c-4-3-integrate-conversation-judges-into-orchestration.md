# Story C4.3: integrate-conversation-judges-into-orchestration

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Developer,
I want conversation judges (DeepEval, GEval, bespoke) to be applied to conversations,
so that holistic conversation-level scoring is supported.

## Acceptance Criteria

1. **Given** conversation judges configured in `eval_config.json`, **When** executed, **Then** each conversation judge receives the entire conversation and produces a holistic score.
2. **Given** conversation judge types: DeepEval (out-of-box), GEval (manual config), Bespoke (custom), **When** applied, **Then** each type executes via the unified `Judge` interface.
3. **Given** multiple conversation judges of different types, **When** applied to one conversation, **Then** all conversation judges execute and all results are collected.
4. **Given** a conversation judge execution, **When** completed, **Then** the result is marked as `judge_type="conversation"`.

## Tasks / Subtasks

- [ ] Implement `ConversationJudge` logic within `DeepEvalJudge` (AC: 1, 2)
  - [ ] Bridge to DeepEval conversation metrics (e.g., `ConversationCoherenceMetric`)
- [ ] Implement `ConversationJudge` logic for `GEvalJudge` (AC: 1, 2)
  - [ ] Configure GEval to evaluate the entire transcript against high-level goals
- [ ] Ensure `BespokeJudge` can handle full transcripts for conversation-level logic (AC: 2)
- [ ] Update `JudgeExecutor` to support holistic conversation evaluation batching (AC: 3)
- [ ] Add unit tests for conversation-level judging (AC: 4)

## Dev Notes

- **Holistic Assessment:** Unlike turn judges, these look at the "arc" of the conversation, goal achievement, and overall coherence.
- **DeepEval Integration:** Use DeepEval's `ConversationalTestCase` or similar if available, or map the full transcript into a single `LLMTestCase` for metrics that support it.
- **Reference:** [Source: _bmad-output/planning-artifacts/tdd-conversational-eval.md#3.2 Conversation-Level Judging]

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
- tests/unit/judges/test_conversation_judging.py
