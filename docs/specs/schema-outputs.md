# gavel-ai Output Schema Reference

This document describes all output artifact schemas produced by a gavel-ai evaluation run.

For the request/response payload schemas exchanged with external systems under test or judges
(HTTP and script transports), see [schema-external-runner.md](schema-external-runner.md).

Run artifacts are stored under `.gavel/evaluations/{eval_name}/runs/{run_id}/`.

---

## Directory Layout

```
.gavel/evaluations/{eval_name}/
├── config/
│   ├── eval_config.json
│   ├── agents.json
│   ├── prompts/
│   │   └── {name}.toml
│   └── judges/
│       └── {name}.toml
├── data/
│   └── scenarios.json
└── runs/
    └── {run_id}/
        ├── .config/                    # Snapshot of configs used for this run
        │   ├── eval_config.json
        │   ├── agents.json
        │   ├── prompts/
        │   └── snapshot_metadata.json
        ├── .workflow_status            # Step completion log (JSONL, append-only)
        ├── results_raw.jsonl           # OutputRecord per scenario × variant
        ├── results_judged.jsonl        # JudgedRecord per scenario × variant × judge
        ├── telemetry.jsonl             # TelemetrySpan records
        ├── run_metadata.json           # Run summary
        └── report.html                 # Generated HTML report
```

---

## results_raw.jsonl

One JSON record per line. Each record is an `OutputRecord` — the raw processor output before judging.

| Field | Type | Description |
|-------|------|-------------|
| `test_subject` | `string` | Test subject identifier (prompt name or remote system ID) |
| `variant_id` | `string` | Model/agent variant ID used for this execution |
| `scenario_id` | `string` | Scenario identifier from scenarios.json |
| `processor_output` | `string` | Raw string output from the model |
| `timing_ms` | `integer` | Execution wall-clock time in milliseconds |
| `tokens_prompt` | `integer` | Prompt tokens consumed |
| `tokens_completion` | `integer` | Completion tokens generated |
| `error` | `string \| null` | Error message if execution failed; `null` on success |
| `metadata` | `object` | Additional metadata (e.g., `turn_number` for conversational runs) |
| `timestamp` | `string` | ISO 8601 timestamp of execution |

**`metadata` keys for externally-executed records** (`test_subject_type: "external"`):

| Key | Type | Description |
|-----|------|-------------|
| `trace_id` | `string` | The Gavel run ID forwarded as an HTTP header to the external system. Resolvable to a span in `telemetry.jsonl` for the same `run_id` (FR-4.3, ADR-2). **Absent on in-process (`local`) records.** |
| `external_outcome` | `string` | Transport-observed outcome: `"process_failure"` or `"process_success_with_issue"`. Present only when `error` is non-null. |
| `external_tier` | `string` | Pre-computed `IssueTier` (`"ERROR"` or `"WARNING"`) derived by `classify_external_outcome` from `external_outcome` and the `abort_on_*` flags. Used by the pipeline's `should_halt` path without re-deriving the tier. |

**Join key:** `(test_subject, variant_id, scenario_id)`

---

## results_judged.jsonl

One JSON record per line. Each record is a `JudgedRecord` — one judge evaluation per `OutputRecord`.

| Field | Type | Description |
|-------|------|-------------|
| `test_subject` | `string` | Test subject identifier |
| `variant_id` | `string` | Model/agent variant ID |
| `scenario_id` | `string` | Scenario identifier |
| `judge_id` | `string` | Judge name from eval_config.json |
| `score` | `integer` | Score on 1–10 scale (normalized from raw 0.0–1.0) |
| `reasoning` | `string \| null` | Judge's explanation; `null` if evaluation errored |
| `error` | `string \| null` | Error message if judging failed; `null` on success |
| `timestamp` | `string` | ISO 8601 timestamp of evaluation |

**Join key:** `(test_subject, variant_id, scenario_id)` joins to `results_raw.jsonl`.

**Score normalization:** DeepEval raw scores (0.0–1.0) are normalized using `round(1 + raw * 9)`, mapping 0.0 → 1 and 1.0 → 10.

---

## run_metadata.json

Single JSON object. Run-level summary produced after all steps complete.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `string` | Run start time (ISO 8601) |
| `config_hash` | `string` | SHA-256 hash of all config files for reproducibility verification |
| `scenario_count` | `integer` | Number of scenarios executed |
| `variant_count` | `integer` | Number of model variants tested |
| `judge_versions` | `object[]` | List of judge version descriptors: `[{"name": ..., "version": ...}]` |
| `status` | `"completed" \| "failed" \| "partial"` | Run completion status |
| `duration` | `float` | Total run time in seconds |
| `metadata` | `object` | Custom key-value metadata pairs |
| `is_milestone` | `boolean` | Whether this run is marked as a milestone |
| `milestone_comment` | `string \| null` | Comment explaining the milestone designation |
| `milestone_timestamp` | `string \| null` | ISO 8601 timestamp when milestone was set |

---

## telemetry.jsonl

One JSON record per line. Each record is a `TelemetrySpan` — an OpenTelemetry-compatible tracing span.

| Field | Type | Description |
|-------|------|-------------|
| `span_id` | `string` | Unique span identifier |
| `trace_id` | `string` | Trace identifier (shared across all spans in one run) |
| `parent_span_id` | `string \| null` | Parent span ID for nested operations |
| `name` | `string` | Operation name (e.g. `"judge.evaluate"`, `"processor.run"`) |
| `start_time` | `string` | ISO 8601 start timestamp |
| `end_time` | `string` | ISO 8601 end timestamp |
| `duration_ms` | `float` | Span duration in milliseconds |
| `status` | `string` | Span status: `"OK"` or `"ERROR"` |
| `attributes` | `object` | Key-value span attributes (e.g. `run_id`, `judge.id`, `scenario.id`) |
| `events` | `object[]` | Span events (exceptions, log messages) |

**Common attributes:**

| Attribute | Description |
|-----------|-------------|
| `run_id` | Current run identifier |
| `judge.id` | Judge name |
| `judge.name` | DeepEval metric type |
| `judge.score` | Normalized score (1–10) |
| `scenario.id` | Scenario identifier |

---

## .config/ Snapshot Directory

Created by `snapshot_run_config()` at the start of each run. Captures the exact configs used for reproducibility.

```
.config/
├── eval_config.json          # Copy of config/eval_config.json at run time
├── agents.json               # Copy of config/agents.json at run time
├── prompts/                  # Copy of all prompt files used
│   └── {name}.toml
└── snapshot_metadata.json    # Snapshot metadata
```

### snapshot_metadata.json

| Field | Type | Description |
|-------|------|-------------|
| `snapshot_time` | `string` | ISO 8601 timestamp when snapshot was created |
| `eval_name` | `string` | Evaluation name |
| `run_id` | `string` | Run identifier this snapshot belongs to |
| `files_copied` | `string[]` | List of file paths included in the snapshot |

---

## .workflow_status

Append-only JSONL file recording step completions. Each line is a JSON object:

| Field | Type | Description |
|-------|------|-------------|
| `step` | `string` | Step phase name: `"prepare"`, `"validation"`, `"scenario_processing"`, `"judging"`, `"reporting"` |
| `completed_at` | `string` | ISO 8601 timestamp of completion |

Steps are written in execution order. A run is complete when all five phases appear.

For autotune runs, `step` additionally includes `"autotune_iteration"` and `"tuning"`
(`StepPhase.AUTOTUNE_ITERATION` / `StepPhase.TUNING`).

---

## Autotune Run Artifacts

Produced by `AutotuneWorkflow` (`workflow_type = "autotune"`) in addition to the standard
run artifacts above. Each run executes an iterative execute → judge → rewrite loop; every
iteration gets its own subdirectory plus a top-level prompt-version ledger and run summary.

```
runs/{run_id}/
├── prompts.toml                # Run-local prompt version ledger (v1, v2, v3, ...)
├── run_summary.json            # AutotuneRunSummary — overall run result
├── report.html                 # AutotuneReporter output (Score Progression, Per-Judge
│                               #   Detail, Best Prompt Version, Run Summary sections)
└── iterations/
    └── iteration_{N}/
        ├── output_raw.jsonl    # OutputRecord per scenario for this iteration
        ├── output_judged.jsonl # JudgedRecord per scenario × judge for this iteration
        └── metadata.json       # IterationMetadata — this iteration's scored result
```

### prompts.toml

Run-local prompt version ledger — **not** the eval's permanent `config/prompts/{name}.toml`.
`v1` is seeded from the eval's current prompt by the `PrepareStep` at run start; each
subsequent version is appended by `TuneStep` after a judged iteration. The eval's permanent
prompt file is never modified during a run (keeps the eval directory immutable/race-free
across concurrent runs).

```toml
[metadata]
name = "my_prompt"
run_id = "run-20260607-173100"

[v1]
prompt = "Original seed prompt text with {{variable}}..."

[v2]
prompt = "LLM-rewritten prompt text with {{variable}}..."
iteration = 1
avg_score = 0.742
```

| Field | Present on | Type | Description |
|-------|-----------|------|-------------|
| `prompt` | all versions | `string` | Full prompt text used for that iteration (`{{var}}` syntax) |
| `iteration` | `v2+` | `integer` | 1-based iteration number that produced this version |
| `avg_score` | `v2+` | `float` | Judged score (0.0–1.0, normalized) that triggered this rewrite |

To promote a winning version permanently, copy its `prompt` text into
`config/prompts/{name}.toml` as a new version — this is a manual Builder step (the HTML
report shows the exact source path and a ready-to-copy `pre` block).

### iterations/iteration_{N}/metadata.json

One `IterationMetadata` object per completed iteration.

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | `integer` | 1-based iteration number |
| `prompt_version` | `string` | Prompt version used this iteration, e.g. `"v1"`, `"v2"` |
| `score` | `float` | Mean normalized score across all scenarios and LLM judges (0.0–1.0) |
| `improvement` | `float` | `current_score - previous_score` (`0.0` for iteration 1) |
| `judge_scores` | `object` | `{judge_name: mean_score}` per-judge breakdown (drives the report's Per-Judge Detail section) |
| `converged` | `boolean` | Whether this iteration triggered convergence |
| `convergence_reason` | `string \| null` | One of `"max_rounds_reached"`, `"target_score_achieved"`, `"minimal_improvement"`, `"performance_degraded"`, or `null` |

**Score normalization:** DeepEval GEval judges return raw scores on a 0–10 scale; these are
divided by 10.0 before being averaged into `score`/`judge_scores`. Deterministic
`classifier`/`regression` judges already produce 0/1 scores and pass through unchanged.

### run_summary.json

Single `AutotuneRunSummary` JSON object — the overall result of the autotune run, consumed
by `AutotuneReporter` to render `report.html`.

| Field | Type | Description |
|-------|------|-------------|
| `eval_name` | `string` | Evaluation name |
| `run_id` | `string` | Run identifier |
| `total_iterations` | `integer` | Number of iterations executed |
| `best_iteration` | `integer` | 1-based number of the highest-scoring iteration |
| `best_score` | `float` | Score of the best iteration (0.0–1.0, normalized) |
| `final_score` | `float` | Score of the last completed iteration (0.0–1.0, normalized) |
| `converged` | `boolean` | Whether the run converged before exhausting `max_rounds` |
| `convergence_reason` | `string \| null` | Same enum as `IterationMetadata.convergence_reason` |
| `iterations` | `IterationMetadata[]` | Full per-iteration history, in order |
