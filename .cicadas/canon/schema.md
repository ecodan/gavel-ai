# Schema Reference

> Canon document. Authoritative as-implemented file format reference for gavel-ai.
> Updated by the Synthesis agent at the close of each initiative.
>
> **Source of truth**: This document reflects what the code actually reads and writes.
> Where this conflicts with BMAD planning artifacts, the code wins.

---

## Directory Layout

```
.gavel/
└── evaluations/
    └── {eval_name}/
        ├── config/
        │   ├── eval_config.json      ← evaluation config
        │   ├── agents.json           ← model + agent definitions
        │   ├── prompts/
        │   │   └── {name}.toml       ← versioned prompt templates
        │   └── judges/               ← optional external judge configs
        │       └── {name}.json
        ├── data/
        │   └── scenarios.json        ← test scenarios array
        └── runs/
            └── {run_id}/
                ├── .config/          ← immutable config snapshot
                │   ├── eval_config.json
                │   ├── agents.json
                │   └── scenarios.json
                ├── results_raw.jsonl       ← OutputRecord rows (immutable)
                ├── results_judged.jsonl    ← combined output + judges
                ├── manifest.json           ← run summary + milestone flags
                ├── report.html             ← rendered report
                ├── telemetry.jsonl         ← OTel spans
                └── run.log                 ← structured execution log
```

---

## Configuration Files

### `eval_config.json`

Pydantic model: `gavel_ai.models.config.EvalConfig`

```json
{
  "eval_type": "oneshot | conversational | autotune",
  "workflow_type": "oneshot | conversational",
  "eval_name": "string",
  "description": "string (optional)",
  "test_subject_type": "local | remote",
  "test_subjects": [
    {
      "prompt_name": "string (required if local)",
      "system_id": "string (required if remote)",
      "protocol": "acp | open_ai (remote only, optional)",
      "config": {},
      "judges": [
        {
          "name": "string (unique per test subject)",
          "type": "deepeval.geval | deepeval.faithfulness | ...",
          "model": "string (shorthand for config.model, optional)",
          "config": {
            "model": "string (model key from agents.json._models)",
            "criteria": "string (required for geval)",
            "evaluation_steps": ["string"],
            "threshold": 0.7
          },
          "config_ref": "string (path to judges/{name}.json, optional)",
          "threshold": 0.7,
          "criteria": "string (top-level shorthand, optional)",
          "evaluation_steps": ["string"]
        }
      ]
    }
  ],
  "variants": ["model-key-from-agents-json"],
  "scenarios": {
    "source": "file.local | file.remote | generator",
    "name": "scenarios.json"
  },
  "execution": {
    "max_concurrent": 5
  },
  "async": {
    "num_workers": 8,
    "arrival_rate_per_sec": 20.0,
    "exec_rate_per_min": 100,
    "max_retries": 3,
    "task_timeout_seconds": 300,
    "stuck_timeout_seconds": 600,
    "emit_progress_interval_sec": 10
  },
  "conversational": {
    "max_turns": 10,
    "max_turn_length": 2000,
    "max_duration_ms": 300000,
    "turn_generator": {
      "model_id": "string",
      "temperature": 0.0,
      "max_tokens": 500
    },
    "elaboration": {
      "enabled": false,
      "elaboration_template": "string (optional)",
      "model_id": "string (optional)"
    },
    "retry_config": {
      "max_retries": 3,
      "initial_delay_ms": 1000,
      "max_delay_ms": 30000,
      "backoff_factor": 2.0
    }
  }
}
```

**Notes:**
- `workflow_type` is a code-only field (not in the BMAD spec's JSON example) used for Literal validation. `eval_type` is the user-facing field. Both are stored in the file; `workflow_type` defaults to `"oneshot"`.
- The `"async"` key in the JSON file maps to the `async_config` Python field via Pydantic alias.
- `execution` and `async` are mutually exclusive; `async` takes precedence.
- `conversational` section is required when `workflow_type == "conversational"`.

---

### `agents.json`

Pydantic model: No strict top-level model — loaded as raw dict. Model entries validated ad-hoc.

```json
{
  "_models": {
    "model-key": {
      "model_provider": "anthropic | openai | vertex_ai | ollama | bedrock",
      "model_family": "claude | gpt | gemini | qwen",
      "model_version": "claude-haiku-4-5-20251001",
      "model_parameters": {
        "temperature": 0.7,
        "max_tokens": 4096,
        "top_p": 1.0
      },
      "provider_auth": {
        "api_key": "{{ANTHROPIC_API_KEY}}",
        "base_url": "https://... (optional)"
      }
    }
  },
  "agent-name": {
    "model_id": "model-key",
    "prompt": "prompt-name:v1",
    "model_parameters": {},
    "custom_configs": {}
  }
}
```

**Notes:**
- `_models` keys are the variant IDs referenced in `eval_config.json "variants": [...]`.
- `{{ENV_VAR}}` placeholders in `provider_auth.api_key` are NOT auto-interpolated by gavel-ai; the literal string is passed to the provider SDK.
- Agent entries (non-`_models`) are used for conversational turn generators and judge model resolution.

---

### `prompts/{name}.toml`

```toml
v1 = '''
System prompt text here.
Use {{input}} for scenario input substitution.
'''

v2 = '''
Updated prompt text.
'''
```

**Notes:**
- Version keys must be `v1`, `v2`, ... (sequential integers).
- Reference format in `agents.json`: `"prompt-name:v1"` or `"prompt-name:latest"` (resolves to highest version).
- `{{input}}` is the standard variable for scenario input injection.

---

### `data/scenarios.json`

Pydantic model: `gavel_ai.models.runtime.Scenario` (per element)

```json
[
  {
    "id": "unique-scenario-id",
    "input": "string or {\"key\": \"value\"}",
    "expected_behavior": "string (optional, used by judges)",
    "context": "string (optional)",
    "metadata": {}
  }
]
```

**Notes:**
- `expected_behavior` alias: also accepted as `"expected"` in JSON.
- `id` alias: also accepted as `"scenario_id"` in JSON.
- `input` can be a string or a dict; dict is JSON-serialized before passing to processors.
- `metadata` is passed through to OutputRecord and judge evaluation context.

---

## Run Output Files

### `results_raw.jsonl`

Pydantic model: `gavel_ai.models.runtime.OutputRecord`

One JSON object per line. Immutable after creation. Written incrementally during processor execution.

```json
{
  "test_subject": "prompt-name or system-id",
  "variant_id": "model-key",
  "scenario_id": "scenario-id",
  "processor_output": "string output from LLM",
  "timing_ms": 1250,
  "tokens_prompt": 45,
  "tokens_completion": 22,
  "error": null,
  "metadata": {},
  "timestamp": "2026-01-10T10:30:45.123456+00:00"
}
```

**Notes:**
- `metadata` is optional (defaults to `{}`). The `OutputRecord` model uses `extra="ignore"`.
- `error` is `null` on success; non-null means execution failed but row is still written.
- Written by `ResultsExporter.append_raw_result()` and `ResultsExporter.export_raw_results()`.

> **Spec divergence**: The BMAD `data-schemas-specification.md` lists `metadata` as absent from `OutputRecord`. The code includes it and writes it.

---

### `results_judged.jsonl`

Written by: `ResultsExporter.export_judged_results()` (normal run) and `ReJudge.rejudge_all()` (re-judge command).

One JSON object per line. One row per scenario × variant execution. Judges embedded as array.

```json
{
  "test_subject": "prompt-name or system-id",
  "variant_id": "model-key",
  "scenario_id": "scenario-id",
  "processor_output": "string output from LLM",
  "timing_ms": 1250,
  "tokens_prompt": 45,
  "tokens_completion": 22,
  "error": null,
  "timestamp": "2026-01-10T10:30:45.123456+00:00",
  "judges": [
    {
      "judge_id": "judge-name",
      "score": 8,
      "reasoning": "Explanation text",
      "evidence": "Supporting evidence (optional)"
    }
  ]
}
```

**Notes:**
- The `judges` array contains one entry per judge configured for this test subject.
- `score` is 1–10 (normalized from judge-native scale).
- This is a combined format — processor output fields + embedded judge results.

> **Spec divergence**: The BMAD `file-formats-specification.md` describes `results_judged.jsonl` as flat `JudgedRecord` rows (one row per judge, join required with `results_raw.jsonl`). The code instead writes a combined format with `judges: []` embedded in each row. The combined format is authoritative — it avoids join complexity in the reporter.

---

### `manifest.json`

Written by: `ReportRunnerStep` at the end of a run.

Single JSON object. Used by `gavel oneshot list` and `gavel oneshot milestone`.

```json
{
  "timestamp": "2026-01-10T10:32:15.500000+00:00",
  "run_id": "run-20260110-103200",
  "eval_name": "assistant_quality",
  "config_hash": "sha256hex",
  "scenario_count": 50,
  "variant_count": 1,
  "judge_count": 2,
  "processor_type": "prompt_input | closedbox_input",
  "status": "completed | partial | failed",
  "completed_count": 50,
  "failed_count": 0,
  "start_time_iso": "2026-01-10T10:30:00.000000+00:00",
  "end_time_iso": "2026-01-10T10:32:15.500000+00:00",
  "duration_seconds": 135.5,
  "variants": ["model-key"],
  "is_milestone": false,
  "milestone_comment": null,
  "milestone_timestamp": null
}
```

**Notes:**
- `is_milestone`, `milestone_comment`, `milestone_timestamp` are set by `gavel oneshot milestone`.
- `config_hash` is SHA256 of the snapshotted config files for reproducibility verification.

> **Spec divergence**: The BMAD `file-formats-specification.md` mentions `run_metadata.json` (with `RunMetadata` schema) as the run summary file. The code writes `manifest.json` with a richer schema. `run_metadata.json` is defined in `gavel_ai.telemetry.metadata.RunMetadataSchema` but is not currently written during runs.

---

### `telemetry.jsonl`

OpenTelemetry spans. One span per line in OTel JSON format.

```json
{
  "trace_id": "hex",
  "span_id": "hex",
  "parent_span_id": "hex or null",
  "name": "llm_call | judge_evaluation | scenario_processing",
  "start_time": 1704882645123456789,
  "end_time": 1704882646373456789,
  "attributes": {
    "llm.model": "claude-haiku-4-5-20251001",
    "llm.tokens.prompt": 45,
    "llm.tokens.completion": 22,
    "scenario.id": "scenario-id",
    "variant.id": "model-key"
  },
  "status": {"code": "OK"}
}
```

---

## Key Cross-File Relationships

| Reference | From | To |
|-----------|------|----|
| `variants[*]` | `eval_config.json` | `agents.json._models` keys |
| `test_subjects[].prompt_name` | `eval_config.json` | `prompts/{name}.toml` |
| `test_subjects[].judges[].config.model` | `eval_config.json` | `agents.json._models` keys |
| `agent.model_id` | `agents.json` | `agents.json._models` keys |
| `results_raw.test_subject` | `results_raw.jsonl` | `eval_config.test_subjects[].prompt_name` |
| `results_raw.variant_id` | `results_raw.jsonl` | `eval_config.variants[*]` |
| `results_raw.scenario_id` | `results_raw.jsonl` | `data/scenarios.json[*].id` |
| `results_judged.*` | `results_judged.jsonl` | Superset of `results_raw` fields + `judges[]` |

---

## Score Normalization

All judge scores are normalized to the **1–10 integer scale** regardless of the source judge's native scale.

| Source scale | Normalization formula |
|---|---|
| DeepEval (0.0–1.0 float) | `round(score * 10)`, clamped to [1, 10] |
| Custom judges | Must return 1–10 directly |

---

## Version History

| Date | Change |
|------|--------|
| 2026-04-11 | Initial canon document. Documents actual code format, flags two spec divergences in `results_judged.jsonl` and `manifest.json` vs `run_metadata.json`. |
