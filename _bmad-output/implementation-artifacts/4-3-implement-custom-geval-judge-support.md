# Story 4.3: Implement Custom GEval Judge Support

Status: done

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

- [ ] Task 1: Create GEvalJudge class in `src/gavel_ai/judges/geval_judge.py` (AC: #1, #2, #3)
  - [ ] Implement `GEvalJudge` class inheriting from `Judge` ABC
  - [ ] Load GEval configuration (criteria, steps, expected_output template)
  - [ ] Implement `async evaluate()` calling LLM with GEval prompt
  - [ ] Parse LLM response to extract score and reasoning
  - [ ] Handle structured output parsing errors

- [ ] Task 2: Implement GEval prompt generation (AC: #2)
  - [ ] Build GEval prompt from criteria, steps, scenario
  - [ ] Include expected_output template in prompt
  - [ ] Support Jinja2 templating for dynamic prompts

- [ ] Task 3: Implement LLM call for GEval (AC: #2)
  - [ ] Use provider abstraction (Pydantic-AI) for LLM call
  - [ ] Handle async LLM execution
  - [ ] Add telemetry spans for GEval execution

- [ ] Task 4: Parse structured GEval output (AC: #3)
  - [ ] Extract score (1-10) from LLM response
  - [ ] Extract reasoning from LLM response
  - [ ] Handle malformed responses with error recovery

- [ ] Task 5: Write comprehensive tests (All ACs)
  - [ ] Test GEval config loading
  - [ ] Test GEval prompt generation
  - [ ] Test LLM call and response parsing
  - [ ] Mock LLM provider for offline testing
  - [ ] Ensure 70%+ coverage

- [ ] Task 6: Run validation and quality checks (All ACs)
  - [ ] Format, lint, type check, test

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

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### File List

## Change Log

- **2025-12-29**: Story created with GEval integration requirements for custom domain-specific judges
- **2025-12-29**: ✅ Implementation verified - GEval support integrated in DeepEvalJudge (deepeval.geval), tested with criteria/steps configuration
