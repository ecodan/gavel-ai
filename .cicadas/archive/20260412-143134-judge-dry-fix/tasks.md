---
summary: "Two sequential partitions. Partition 1 (feat/foundation): add typed step-result attrs to LocalRunContext, create storage/utils.py with compute_config_hash, migrate hash tests. Partition 2 (feat/steps-and-cleanup): refactor all three pipeline steps for multi-variant + OutputRecord, rewrite judge CLI, delete ReJudge + ResultsExporter + their tests, update and migrate remaining tests, pass 70% coverage gate."
phase: "tasks"
when_to_load:
  - "When selecting the next implementation task or reviewing completion state."
  - "When checking partition progress or execution sequencing."
depends_on:
  - "prd.md"
  - "tech-design.md"
  - "approach.md"
modules:
  - "core/contexts.py"
  - "core/steps/scenario_processor.py"
  - "core/steps/judge_runner.py"
  - "core/steps/report_runner.py"
  - "cli/commands/oneshot.py"
  - "storage/utils.py"
  - "storage/results_exporter.py"
  - "judges/rejudge.py"
index:
  partition_one: "## Partition: feat/foundation"
  partition_two: "## Partition: feat/steps-and-cleanup"
next_section: "## Partition: feat/foundation"
---

# Tasks: judge-dry-fix

## Partition: feat/foundation

- [x] Add typed step-result attrs to `LocalRunContext.__init__` in `src/gavel_ai/core/contexts.py`: `processor_results: Optional[List[OutputRecord]] = None`, `evaluation_results: Optional[List[Dict[str, Any]]] = None`, `test_subject: Optional[str] = None`, `model_variant: Optional[str] = None`. Add any missing `typing` imports. Run `mypy src/` — must report no new errors. <!-- id: 1 -->
- [x] Create `src/gavel_ai/storage/utils.py` with `compute_config_hash(config_files: Dict[str, Path]) -> str` (copy from `ResultsExporter.compute_config_hash` — do NOT delete `ResultsExporter` yet). Verify `from gavel_ai.storage.utils import compute_config_hash` imports without error. <!-- id: 2 -->
- [x] Create `tests/unit/storage/test_utils.py`. Migrate the 5 `compute_config_hash` test cases from `tests/unit/storage/test_results_exporter.py` — update import to `from gavel_ai.storage.utils import compute_config_hash`. Tests: `test_compute_config_hash_returns_consistent_hash`, `test_compute_config_hash_deterministic_ordering`, `test_compute_config_hash_different_for_different_content`, `test_compute_config_hash_raises_file_not_found`, `test_compute_config_hash_handles_multiple_files`. <!-- id: 3 -->
- [x] Run `pytest -m unit` — all tests pass. Run conversational unit tests and verify `context.test_subject` and `context.model_variant` are still assignable (typed as `Optional[str]`). <!-- id: 4 -->

## Partition: feat/steps-and-cleanup

- [x] In `src/gavel_ai/core/steps/scenario_processor.py`: add `_make_output_record(proc_result, input_item, test_subject, variant_id) -> OutputRecord` helper (see tech-design ADR-2 for field mapping). Add `datetime`, `timezone` imports if not present. <!-- id: 10 -->
- [x] In `scenario_processor.py`: replace the single-variant block with an outer loop over `eval_config.variants`. For each variant: resolve model, instantiate processor, build `inputs`, run executor with `_spool_result` callback. In `_spool_result`: call `_make_output_record()` and `context.results_raw.append(record)` (via `RecordDataSource` — not direct file write). Accumulate into `all_records: List[OutputRecord]`. After the loop: `context.processor_results = all_records`, `context.test_subject = <first variant's test_subject>`, `context.model_variant = ", ".join(eval_config.variants)`. Remove `ResultsExporter` import. <!-- id: 11 -->
- [x] In `src/gavel_ai/core/steps/judge_runner.py`: add `from collections import defaultdict`. Replace `zip(scenarios, processor_results, strict=True)` with: build `scenario_map = {s.id: s for s in scenarios}`, group records by `variant_id` using `defaultdict(list)`, then for each variant group call `judge_executor.execute_batch([(scenario_map[r.scenario_id], r.processor_output, r.variant_id) for r in group], subject_id=test_subject, test_subject=test_subject)`. Flatten results: `context.evaluation_results = [r.model_dump() for r in all_results]`. <!-- id: 12 -->
- [x] In `src/gavel_ai/core/steps/report_runner.py`: replace `exporter.export_judged_results(...)` with an inline join. Build `eval_by_key = {(e["scenario_id"], e["variant_id"]): e for e in evaluation_results}`. For each `record` in `processor_results` call `run_context.results_judged.append({**record.model_dump(exclude={"metadata"}), "judges": eval_by_key.get((record.scenario_id, record.variant_id), {}).get("judges", [])})`. Replace `exporter.compute_config_hash(...)` with `compute_config_hash(...)` from `gavel_ai.storage.utils`. Update `variant_count` in manifest data to `len(eval_config.variants)`. Remove `ResultsExporter` import, add `from gavel_ai.storage.utils import compute_config_hash`. <!-- id: 13 -->
- [x] In `src/gavel_ai/cli/commands/oneshot.py`: rewrite the `judge` command body — load `records: List[OutputRecord] = list(run_ctx.results_raw.read())`, raise `ResourceNotFoundError` if empty, set `run_ctx.processor_results = records` (reuse the existing `run_ctx`, do NOT create a second `LocalRunContext`), `asyncio.run(JudgeRunnerStep(app_logger).execute(run_ctx))`, `asyncio.run(ReportRunnerStep(app_logger).execute(run_ctx))`. Remove `--judges` option. Remove `from gavel_ai.judges.rejudge import ReJudge` import and `get_model_definition` import. Remove all model resolution code from the command. Add `JudgeRunnerStep`, `ReportRunnerStep` imports. <!-- id: 14 -->
- [x] Delete source files and clean up registry: delete `src/gavel_ai/judges/rejudge.py`, delete `src/gavel_ai/storage/results_exporter.py`, remove `ReJudge` from `src/gavel_ai/judges/__init__.py`. Verify: `grep -r "ResultsExporter\|results_exporter\|ReJudge\|rejudge" src/` returns no hits. <!-- id: 15 -->
- [x] Delete test files for deleted source: delete `tests/unit/test_rejudge.py`, delete `tests/unit/storage/test_results_exporter.py`. Verify: `pytest --collect-only -q` reports no import errors. <!-- id: 16 -->
- [x] Update `tests/unit/test_steps.py`: replace `ProcessorResult` mocks with `OutputRecord` mocks in `ScenarioProcessorStep` tests. Add a 2-variant test: mock executor returns results for both variants, assert `context.processor_results` has 2×N records with correct `variant_id` on each. Assert `context.results_raw.append` called 2×N times. <!-- id: 17 -->
- [x] Update `tests/unit/steps/test_judge_runner.py`: update test inputs to pass `List[OutputRecord]` instead of `List[ProcessorResult]` in context. Update any assertion of `variant_id == "subject_agent"` — replace with the actual variant id from the test fixture. Add a multi-variant grouping test: 2 variants × 3 scenarios → 6 `EvaluationResult` dicts in `context.evaluation_results`, each with correct `scenario_id` and `variant_id`. <!-- id: 18 -->
- [x] Update `tests/unit/steps/test_report_runner.py`: update setup to pass `List[OutputRecord]` in `context.processor_results`. Add `evaluation_results` with `scenario_id` and `variant_id` keys. Assert `results_judged.jsonl` entries are joined by `(scenario_id, variant_id)` not by position. Assert no `metadata` key in written entries. Assert `results_raw.jsonl` is untouched. <!-- id: 19 -->
- [x] Run `pytest -m unit` — all tests pass. Then run `pytest --cov=gavel_ai --cov-fail-under=70 -m unit` — coverage gate passes at ≥70%. <!-- id: 20 -->
