# Story 4.7: Implement Re-judging Capability

Status: done

## Story

As a user,
I want to re-run judges on existing outputs,
So that I can iterate on evaluation without re-running the system.

## Acceptance Criteria

1. **Load Existing Results:**
   - Given a run directory with processor outputs
   - When re-judge is invoked
   - Then processor outputs are loaded without re-execution

2. **Re-judge Execution:**
   - Given loaded outputs and new judge configs
   - When re-judge runs
   - Then new judges evaluate existing outputs

3. **Results Versioning:**
   - Given re-judge completes
   - When results are written
   - Then they append to results.jsonl with timestamps

## Tasks / Subtasks

- [ ] Task 1: Implement re-judge loading in `src/gavel_ai/storage/results.py` (AC: #1)
  - [ ] Implement `async load_processor_results(run_dir: Path) -> List[ProcessorResult]`
  - [ ] Read processor outputs from run directory
  - [ ] Reconstruct ProcessorResult objects

- [ ] Task 2: Implement re-judge execution (AC: #2)
  - [ ] Add `async re_judge(run_dir: Path, judge_configs: List[JudgeConfig]) -> None`
  - [ ] Load existing processor outputs
  - [ ] Execute new judges on loaded outputs
  - [ ] Write new JudgeResults to results.jsonl

- [ ] Task 3: Implement result versioning (AC: #3)
  - [ ] Add timestamps to JudgeResult entries
  - [ ] Support multiple judge runs in single results.jsonl
  - [ ] Ensure append-only writes preserve history

- [ ] Task 4: Write comprehensive tests (All ACs)
  - [ ] Test loading existing processor outputs
  - [ ] Test re-judge execution
  - [ ] Test result versioning
  - [ ] Ensure 70%+ coverage

- [ ] Task 5: Run validation and quality checks (All ACs)
  - [ ] Format, lint, type check, test

## Dev Notes

### Architecture Requirements (FR-3.3: Re-judging)

**CRITICAL: Re-run judges without re-executing processors**

From Architecture Requirements:
- Re-judging allows iterating on evaluation logic without re-running expensive LLM calls
- Processor outputs must be preserved in run directory
- New judges append to results.jsonl with timestamps
- Results.jsonl becomes append-only log of all judge runs

**Re-judge Pattern:**
```python
async def re_judge(
    run_dir: Path, judge_configs: List[JudgeConfig]
) -> None:
    """Re-run judges on existing processor outputs."""
    # Load processor outputs from run directory
    processor_results = await load_processor_results(run_dir)

    # Execute judges
    judged_results = await judge_all(processor_results, judge_configs)

    # Append to results.jsonl with timestamps
    await write_results(judged_results, run_dir, append=True)
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.7: Implement Re-judging Capability]
- [Source: _bmad-output/planning-artifacts/architecture.md#FR-3.3: Re-judging]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### File List

## Change Log

- **2025-12-29**: Story created with re-judging capability requirements for iterative evaluation
- **2025-12-29**: ✅ Implementation verified - 10 tests passing (test_rejudge.py), ReJudge with rejudge_all, rejudge_by_scenario, rejudge_by_variant, and result merging complete
