# Story C4.5: wire-judge-configuration-and-factory-for-all-judge-types

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a User,
I want any judge type (DeepEval, GEval, bespoke) defined in eval_config.json,
so that judges can be modified without code changes.

## Acceptance Criteria

1. **Given** `eval_config.json` includes `judges` array with `judge_type` (turn|conversation) and `judge_class` (deepeval|geval|custom), **When** loaded, **Then** judges are parsed correctly.
2. **Given** `judge_class="deepeval"`, **When** executed, **Then** the appropriate `DeepEvalJudge` is loaded and applied.
3. **Given** `judge_class="geval"`, **When** executed, **Then** the `GEvalJudge` is loaded and applied with the custom metric definition.
4. **Given** `judge_class="custom"`, **When** executed, **Then** the custom `BespokeJudge` is loaded and applied.
5. **Given** an invalid judge configuration, **When** loaded, **Then** a `JudgeError` or `ConfigError` is raised with helpful guidance.

## Tasks / Subtasks

- [ ] Update `JudgeConfig` and `EvalConfig` models in `src/gavel_ai/models/config.py` (AC: 1)
  - [ ] Add `judge_type` (Enum: turn, conversation)
  - [ ] Add `judge_class` (Enum: deepeval, geval, custom)
- [ ] Enhance `JudgeRegistry` or create `JudgeFactory` (AC: 2, 3, 4)
  - [ ] Support dynamic instantiation based on `judge_class`
  - [ ] Handle registration of bespoke judge classes
- [ ] Implement validation logic for judge configurations (AC: 5)
- [ ] Update CLI scaffolding to provide examples of all three judge types (AC: 1)
- [ ] Add unit tests for configuration parsing and factory instantiation (AC: 1-5)

## Dev Notes

- **Schema Evolution:** This story connects the declarative power of `eval_config.json` to the implementation classes created in C4.1-C4.3.
- **Bespoke Loading:** For `custom` judges, we may need to support a module path (e.g., `my_module.MyJudgeClass`) and load it dynamically.
- **Reference:** [Source: _bmad-output/planning-artifacts/tdd-conversational-eval.md#6. Configuration Schema]

### Project Structure Notes

- Touch `src/gavel_ai/models/config.py`
- Touch `src/gavel_ai/judges/judge_registry.py` (or create `factory.py`)
- Touch `src/gavel_ai/cli/commands/conversational.py` (scaffolding defaults)

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

- src/gavel_ai/models/config.py
- src/gavel_ai/judges/judge_registry.py
- tests/unit/judges/test_judge_factory.py
