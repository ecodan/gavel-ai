# Story 4.6: Implement Result Storage (results.jsonl)

Status: done

## Story

As a user,
I want judged results persisted to results.jsonl,
So that I can analyze evaluation outcomes.

## Acceptance Criteria

1. **JSONL Format:**
   - Given judged results exist
   - When persisted
   - Then each line in results.jsonl is valid JSON

2. **Result Schema:**
   - Given a result line
   - When read
   - Then it contains scenario_id, variant_id, processor_output, judge_id, judge_score, judge_reasoning, judge_evidence

3. **Append-Only Writes:**
   - Given new results
   - When written
   - Then they append to results.jsonl without overwriting

## Tasks / Subtasks

- [ ] Task 1: Create result storage in `src/gavel_ai/storage/results.py` (AC: #1, #2, #3)
  - [ ] Implement `ResultStorage` class
  - [ ] Implement `async write_results(judged_results: List[JudgedResult], run_dir: Path) -> None`
  - [ ] Persist each JudgedResult as JSONL line
  - [ ] Use append-only writes for durability

- [ ] Task 2: Define result schema (AC: #2)
  - [ ] Create result dict with scenario_id, variant_id, processor_output, judge_id, judge_score, judge_reasoning, judge_evidence
  - [ ] Ensure all fields use snake_case
  - [ ] Validate JSON serialization

- [ ] Task 3: Write comprehensive tests (All ACs)
  - [ ] Test JSONL writing
  - [ ] Test result schema
  - [ ] Test append-only behavior
  - [ ] Ensure 70%+ coverage

- [ ] Task 4: Run validation and quality checks (All ACs)
  - [ ] Format, lint, type check, test

## Dev Notes

### Architecture Requirements (Decision 4: Run Artifact Schema & Storage)

**CRITICAL: Results JSONL schema**

From Architecture Document (Decision 4):
```json
{
  "scenario_id": "...",
  "variant_id": "...",
  "processor_output": "...",
  "judge_id": "...",
  "judge_score": 8,
  "judge_reasoning": "...",
  "judge_evidence": "..."
}
```

**Run Directory Structure:**
```
runs/<timestamp>/
├── results.jsonl          # Judged results
├── telemetry.jsonl        # OT spans
├── run_metadata.json      # Performance metrics
└── gavel.log              # Execution log
```

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Decision 4: Run Artifact Schema & Storage]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.6: Implement Result Storage]

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.5 (claude-sonnet-4-5-20250929)

### File List

## Change Log

- **2025-12-29**: Story created with results.jsonl storage requirements and schema definition
- **2025-12-29**: ✅ Implementation verified - ResultStorage with JSONL append-only writes complete, tested via test_result_storage.py and integration with JudgeExecutor
