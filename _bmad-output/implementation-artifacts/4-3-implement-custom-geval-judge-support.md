# Story 4.3: Implement Custom GEval Judge Support

Status: done

✅ **All Acceptance Criteria Met**
- AC#1: GEval Configuration with expected_output_template support ✅
- AC#2: GEval Execution with LLM integration ✅
- AC#3: Structured Output Parsing with score/reasoning extraction ✅

## Story

As a user,
I want custom GEval judges defined declaratively,
So that I can implement domain-specific evaluation logic.

## Acceptance Criteria

1. **GEval Configuration:**
   - Given a judge config references GEval
   - When loaded
   - Then the system reads GEval criteria, steps, and expected_output template

2. **GEval Execution:**
   - Given a GEval judge is configured
   - When evaluate() is called
   - Then the LLM is called with GEval prompt and returns structured score

3. **Structured Output Parsing:**
   - Given the GEval LLM response
   - When parsed
   - Then score (1-10) and reasoning are extracted correctly

## Tasks / Subtasks

- [x] Task 1: Create GEvalJudge class in DeepEvalJudge adapter (AC: #1, #2, #3)
  - [x] Implement GEval support in DeepEvalJudge with criteria, steps, expected_output_template
  - [x] Load GEval configuration from judge config
  - [x] Implement async evaluate() calling DeepEval GEval metric
  - [x] Parse GEval response to extract score and reasoning
  - [x] Handle configuration errors gracefully

- [x] Task 2: Implement GEval expected_output_template rendering (AC: #1)
  - [x] Support Jinja2 templating for dynamic expected outputs
  - [x] Build template context from scenario input and metadata
  - [x] Render template with scenario variables
  - [x] Fall back to scenario.expected when template variables missing

- [x] Task 3: Integrate GEval with LLM provider (AC: #2)
  - [x] Use DeepEval's native GEval implementation (deepeval.geval)
  - [x] Pass LLM model configuration (gpt-4 default)
  - [x] Handle async metric execution via asyncio.to_thread()
  - [x] Add telemetry spans for GEval execution

- [x] Task 4: Parse and normalize GEval output (AC: #3)
  - [x] Extract score (0.0-1.0) from DeepEval metric
  - [x] Normalize to 1-10 integer scale
  - [x] Extract reasoning from metric.reason
  - [x] Handle DeepEval errors with recovery guidance

- [x] Task 5: Write comprehensive tests (All ACs)
  - [x] Test GEval config loading with criteria/steps
  - [x] Test expected_output_template rendering with Jinja2
  - [x] Test fallback when template variables missing
  - [x] Test GEval evaluation with mock DeepEval provider
  - [x] Test score normalization (0.0-1.0 → 1-10)
  - [x] 15 total tests, 100% passing, 4 new template tests

- [x] Task 6: Run validation and quality checks (All ACs)
  - [x] Format with black ✅
  - [x] Lint with ruff ✅
  - [x] Type check with mypy ✅
  - [x] All 15 tests passing ✅

## Dev Notes

### Architecture Requirements (Decision 5: Judge Integration & Plugin System)

**CRITICAL: GEval for custom evaluation logic**

From Architecture Document (Decision 5):
- Custom Judges: GEval for domain-specific evaluation
- GEval judges configured with criteria, steps, expected_output template
- Use DeepEval's GEval implementation: `deepeval.geval`
- Score format: Integer 1-10 scale

**GEval Configuration Example:**
```json
{
  "judge_id": "custom_eval",
  "deepeval_name": "deepeval.geval",
  "config": {
    "criteria": "Evaluates factual accuracy and completeness",
    "steps": [
      "Check if all key facts are present",
      "Verify no contradictions exist",
      "Assess completeness of answer"
    ],
    "expected_output_template": "A complete, factually accurate answer covering {{key_points}}"
  }
}
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5: Judge Integration & Plugin System]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3: Implement Custom GEval Judge Support]
- [Source: _bmad-output/implementation-artifacts/4-1-create-judge-base-class-and-interface.md]

## Dev Agent Record

### Agent Model Used

Claude Haiku 4.5 (claude-haiku-4-5-20251001)

### Debug Log References

**Code Review Issues Found & Fixed (2026-01-03):**
- expected_output_template feature not implemented (AC#1 requirement)
- GEval test fixtures missing template configuration
- Missing test coverage for template rendering
- Story status inconsistency (done but tasks unmarked)
- Empty file list (no documentation of changed files)

### Completion Notes List

1. **Expected Output Template Implementation**: Added full Jinja2 template rendering support for `expected_output_template` in GEval config
2. **Smart Template Resolution**: Implemented priority-based resolution:
   - Render expected_output_template if available AND all variables present
   - Fall back to scenario.expected when template variables missing
   - Graceful error handling with logging
3. **Template Context**: Template context built from scenario.input (dict fields) and scenario.metadata
4. **Test Coverage**: Added 4 new comprehensive tests covering:
   - Basic template rendering with variables
   - Template usage in test case creation
   - Fallback behavior when variables missing
   - Backward compatibility without template
5. **Validation**: All 15 tests passing (11 original + 4 new template tests)

### File List

- **src/gavel_ai/judges/deepeval_judge.py** - Enhanced with expected_output_template support and _get_expected_output() helper
- **tests/unit/test_deepeval_judge.py** - Added geval_config_with_template fixture and TestGEvalExpectedOutputTemplate test class (4 tests)
- **Story 4-3 documentation** - Updated tasks, file list, and completion notes

## Change Log

- **2025-12-29**: Story created with GEval integration requirements for custom domain-specific judges
- **2025-12-29**: ✅ Implementation verified - GEval support integrated in DeepEvalJudge (deepeval.geval), tested with criteria/steps configuration
- **2026-01-03**: 🔥 Code Review - Found 5 medium/low issues with missing expected_output_template feature and incomplete documentation
- **2026-01-03**: ✅ Implemented expected_output_template with Jinja2 rendering, smart fallback behavior, and comprehensive tests
- **2026-01-03**: ✅ All 15 tests passing - GEval custom judge support fully implemented per AC requirements
