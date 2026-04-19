# gavel-ai Output Schema Reference

This document describes all output artifact schemas produced by a gavel-ai evaluation run.

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
