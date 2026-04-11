# Story C4.1: implement-unified-judge-interface

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a Developer,
I want a single Judge interface that supports DeepEval, GEval, and bespoke judges,
so that all judge types work consistently.

## Acceptance Criteria

1. **Given** Judge base class/interface exists, **When** examined, **Then** it has: `async evaluate(conversation: ConversationResult, scenario: Scenario, variant_id: str, scenario_id: str) -> JudgeResult` (or similar unified signature).
2. **Given** `evaluate()` is called, **When** completed, **Then** `JudgeResult` contains: `judge_id`, `judge_name`, `judge_score` (1-10), `judge_reasoning`, `judge_evidence`.
3. **Given** judge receives full conversation as input, **When** executed, **Then** entire conversation transcript is available for judging.
4. **Given** judge implementations created (`DeepEvalJudge`, `GEvalJudge`, `BespokeJudge` subclasses), **When** examined, **Then** each inherits from `Judge` interface and implements `evaluate()`.
5. **Given** judge result created, **When** examined, **Then** it includes metadata: `scenario_id`, `variant_id`, `judge_type` (turn|conversation), `judge_class_name`.

## Tasks / Subtasks

- [ ] Define / Update `Judge` abstract base class in `src/gavel_ai/judges/base.py` (AC: 1)
  - [ ] Update `evaluate` signature to support conversational data
  - [ ] Ensure backward compatibility for OneShot (where transcript is not available)
- [ ] Implement `DeepEvalJudge` subclass (AC: 4)
  - [ ] Bridge to DeepEval metrics (e.g., `AnswerRelevancyMetric`, `FaithfulnessMetric`)
- [ ] Implement `GEvalJudge` subclass (AC: 4)
  - [ ] Support custom criteria from eval_config
- [ ] Implement `BespokeJudge` subclass (AC: 4)
  - [ ] Allow users to provide custom Python classes for judging
- [ ] Update `JudgeResult` model in `src/gavel_ai/models/runtime.py` to include metadata (AC: 2, 5)
  - [ ] Add `judge_type` (turn/conversation)
  - [ ] Add `judge_class_name`
- [ ] Add unit tests for the unified interface (AC: 1-5)
  - [ ] Test with mock conversations and scenarios

## Dev Notes

- **Architecture Compliance:** Per TDD, Conversational extends gavel-ai's Step-based architecture. The Judge interface must handle both OneShot (isolated prompt-response) and Conversational (multi-turn).
- **Signature Refinement:** To unify, use `async def evaluate(self, scenario: Scenario, subject_output: str, conversation: Optional[ConversationResult] = None) -> JudgeResult`. For OneShot, `conversation` is `None`. For Conversational, `conversation` provides the full context.
- **DeepEval Integration:** Continue using DeepEval as the primary judging engine but wrap it in the new interface.
- **Reference:** [Source: _bmad-output/planning-artifacts/tdd-conversational-eval.md#3. Enhanced JudgeRunnerStep]

## Technical Requirements

- **Unified Interface:** The `Judge.evaluate` method must be the single entry point for all judging logic.
- **Context Availability:** Judges must have access to the full `ConversationResult` (transcript, timing, tokens) to enable holistic evaluation.
- **Pydantic Validation:** All models must follow the existing patterns in `src/gavel_ai/models/runtime.py`.
- **Async Execution:** All `evaluate` calls must be asynchronous to support parallel judging.
- **Standardized Output:** `JudgeResult` must be compatible with the existing `results_judged.jsonl` export logic.

## Architecture Compliance

- **Step-Based Design:** The judges will be orchestrated by `JudgeRunnerStep` which must be enhanced (in a later story) to support this new interface.
- **Pattern Reuse:** Re-use the `JudgeConfig` and `JudgeResult` patterns established in Epic 4.
- **Determinism:** Temperature for LLM-based judges (DeepEval, GEval) must be set to 0.0 by default.
- **Separation of Concerns:** Judging logic should be decoupled from the data sources, receiving only the necessary models.

### Project Structure Notes

- Touch `src/gavel_ai/judges/base.py`
- Touch `src/gavel_ai/models/runtime.py`
- New files: `src/gavel_ai/judges/deepeval_judge.py`, `src/gavel_ai/judges/geval_judge.py`, `src/gavel_ai/judges/bespoke_judge.py` or similar.

### References

- [_bmad-output/planning-artifacts/epics-conversational-eval.md](_bmad-output/planning-artifacts/epics-conversational-eval.md)
- [_bmad-output/planning-artifacts/tdd-conversational-eval.md](_bmad-output/planning-artifacts/tdd-conversational-eval.md)
- [src/gavel_ai/judges/base.py](src/gavel_ai/judges/base.py)

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 2.0 Flash Thinking)

### Debug Log References

None

### Completion Notes List

None

### File List

- src/gavel_ai/judges/base.py
- src/gavel_ai/models/runtime.py
- src/gavel_ai/judges/deepeval_judge.py
- src/gavel_ai/judges/geval_judge.py
- src/gavel_ai/judges/bespoke_judge.py
- tests/unit/judges/test_unified_judge.py
