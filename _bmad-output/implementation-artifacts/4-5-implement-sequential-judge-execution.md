# Story 4.5: Implement Sequential Judge Execution

Status: done

## Story

As a system,
I want to execute judges sequentially,
So that all outputs are scored by all judges in order.

## Acceptance Criteria

1. **Sequential Execution:**
   - Given multiple judges are configured
   - When execution starts
   - Then Judge A evaluates all outputs before Judge B starts

2. **Judge Orchestration:**
   - Given ProcessorResults and Judge configs
   - When judge_all() is called
   - Then all results are judged by all configured judges

3. **Results Collection:**
   - Given judges complete
   - When results are collected
   - Then each ProcessorResult has JudgeResults from all judges

## Tasks / Subtasks

- [ ] Task 1: Create judge orchestrator in `src/gavel_ai/judges/orchestrator.py` (AC: #1, #2, #3)
  - [ ] Implement `async judge_all(results: List[ProcessorResult], judge_configs: List[JudgeConfig]) -> List[JudgedResult]`
  - [ ] Execute judges sequentially (all outputs with judge A, then judge B, etc.)
  - [ ] Collect JudgeResults and attach to ProcessorResults
  - [ ] Add telemetry spans for orchestration

- [ ] Task 2: Define JudgedResult model (AC: #3)
  - [ ] Create JudgedResult Pydantic model
  - [ ] Include ProcessorResult + List[JudgeResult]
  - [ ] Ensure proper type hints and validation

- [ ] Task 3: Write comprehensive tests (All ACs)
  - [ ] Test sequential judge execution order
  - [ ] Test multiple judges on multiple results
  - [ ] Mock judges for offline testing
  - [ ] Ensure 70%+ coverage

- [ ] Task 4: Run validation and quality checks (All ACs)
  - [ ] Format, lint, type check, test

## Dev Notes

### Architecture Requirements (Decision 5: Judge Integration & Plugin System)

**CRITICAL: Sequential execution model**

From Architecture Document (Decision 5):
- Execution Model: Sequential (judge all results with judge A, then B, etc.)
- Each ProcessorResult is scored by all configured judges
- Results stored with judge_id to identify which judge scored

**Sequential Execution Pattern:**
```python
async def judge_all(
    results: List[ProcessorResult],
    judge_configs: List[JudgeConfig],
) -> List[JudgedResult]:
    """Execute all judges sequentially against all results."""
    judged_results = []

    for result in results:
        judge_scores = []
        for judge_config in judge_configs:
            judge = create_judge(judge_config)
            score = await judge.evaluate(result.scenario, result.output)
            judge_scores.append(score)
        judged_results.append(JudgedResult(result=result, scores=judge_scores))

    return judged_results
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 5: Judge Integration & Plugin System]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.5: Implement Sequential Judge Execution]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### File List

## Change Log

- **2025-12-29**: Story created with sequential judge execution orchestration requirements
- **2025-12-29**: ✅ Implementation verified - 12 tests passing (test_judge_executor.py), JudgeExecutor with sequential execution, error handling (fail_fast/continue_on_error), and batch support complete
