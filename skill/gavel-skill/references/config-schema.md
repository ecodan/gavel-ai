# Gavel Config Schema Reference

> Authoritative field reference derived from canon/schema.md and Pydantic models.
> When this document conflicts with scaffolded file comments, the code wins.

---

## Directory Layout

```
.gavel/evaluations/{eval_name}/
├── config/
│   ├── eval_config.json      ← evaluation config (required)
│   ├── agents.json           ← model + agent definitions (required)
│   ├── prompts/
│   │   └── {name}.toml       ← versioned prompt templates
│   └── judges/
│       └── {name}.json       ← optional external judge configs
├── data/
│   └── scenarios.json        ← test scenario array
└── runs/
    └── {run_id}/
        ├── results_raw.jsonl
        ├── results_judged.jsonl
        ├── manifest.json
        └── report.html
```

---

## `eval_config.json`

Pydantic model: `gavel_ai.models.config.EvalConfig`

### Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `eval_type` | `"oneshot" \| "conversational" \| "autotune"` | Yes | Evaluation workflow type |
| `workflow_type` | `"oneshot" \| "conversational"` | Auto | Code-internal field; defaults to `"oneshot"`. Set automatically — do not change manually. |
| `eval_name` | string | Yes | Matches the directory name under `.gavel/evaluations/` |
| `description` | string | No | Human-readable description of this eval |
| `test_subject_type` | `"local" \| "remote"` | Yes | `"local"` = prompt-based; `"remote"` = in-situ system |
| `test_subjects` | array | Yes | One or more test subjects (see below) |
| `variants` | string[] | No | List of model keys from `agents.json._models` to test |
| `scenarios` | object | Yes | Scenario source config (see below) |
| `execution` | object | No | Simple concurrency config (mutually exclusive with `async`) |
| `async` | object | No | Advanced async config (takes precedence over `execution`) |
| `conversational` | object | Cond. | Required when `eval_type == "conversational"` |

### `test_subjects[]`

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt_name` | string | If local | Name of prompt in `prompts/` (without `.toml`) |
| `system_id` | string | If remote | Identifier for the remote system under test |
| `protocol` | `"acp" \| "open_ai"` | No | Remote protocol (remote only) |
| `config` | object | No | Additional subject config |
| `judges` | array | No | Judges applied to this subject's output |

### `test_subjects[].judges[]`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Unique judge name within this test subject |
| `type` | string | Yes | Judge type identifier (e.g., `"deepeval.geval"`) |
| `model` | string | No | Shorthand for `config.model` |
| `threshold` | float | No | Pass/fail threshold (0.0–1.0 for deepeval, or 1–10 for score comparison). Defaults to `0.7`. |
| `criteria` | string | No | Top-level shorthand for `config.criteria` (geval) |
| `evaluation_steps` | string[] | No | Top-level shorthand for `config.evaluation_steps` (geval) |
| `config` | object | No | Judge-specific config (see below and `references/judges-reference.md`) |
| `config_ref` | string | No | Path to external judge config TOML in `config/judges/` |

#### `judges[].config` for `deepeval.geval`

| Field | Type | Default | Description |
|---|---|---|---|
| `model` | string | — | Model key from `agents.json` |
| `criteria` | string | — | One sentence describing what "good" looks like |
| `evaluation_steps` | string[] | — | 3–6 concrete checks evaluated in order |
| `threshold` | float | `0.7` | Pass/fail cutoff (0.0–1.0 raw DeepEval scale) |
| `strict_mode` | bool | `false` | Return binary 0/1 score instead of continuous. Normalizes to score 1 or 10. |
| `expected_output_template` | string | — | Jinja2 template rendered with `scenario.input` fields + `scenario.metadata` |

`evaluation_params` is always `[INPUT, ACTUAL_OUTPUT, EXPECTED_OUTPUT]`. Values are resolved from `scenarios.field_mapping` or `scenario.expected_behavior` — see `scenarios.field_mapping` above.

### `scenarios`

| Field | Type | Required | Description |
|---|---|---|---|
| `source` | `"file.local" \| "file.remote" \| "generator"` | Yes | Where scenarios come from |
| `name` | string | Yes | Filename (e.g., `"scenarios.json"`) |
| `field_mapping` | object | No | Maps scenario file fields → GEval test-case params (see below) |

#### `scenarios.field_mapping`

Declares how to extract GEval test-case params from each scenario record using **dot-notation paths**.
Configured once per eval; applies to every `deepeval.geval` judge in the run.

| Sub-field | Type | Description |
|---|---|---|
| `input` | string | Dot-notation path to input text (e.g., `"input.query"`). Defaults to `input.text` → `input.query` → `str(input)`. |
| `expected_output` | string | Dot-notation path to expected/golden output (e.g., `"expected_output"`, `"metadata.golden"`). Defaults to `scenario.expected_behavior`. |
| `actual_output` | string | Dot-notation path to pre-generated output (overrides live processor output). Only needed for offline re-judging. |

**Validation**: If any GEval judge is configured and a scenario cannot resolve `expected_output`
(via `field_mapping.expected_output` or the `expected_behavior` fallback), gavel raises
`ConfigError` before any API call.

**Example** (scenario file uses `"expected_output"` field):
```json
"scenarios": {
  "source": "file.local",
  "name": "scenarios.json",
  "field_mapping": {
    "expected_output": "expected_output"
  }
}
```

**Example** (expected output nested in metadata):
```json
"scenarios": {
  "source": "file.local",
  "name": "scenarios.json",
  "field_mapping": {
    "input": "input.query",
    "expected_output": "metadata.golden_schema"
  }
}
```

### `execution` (simple concurrency)

| Field | Type | Default | Description |
|---|---|---|---|
| `max_concurrent` | int | 5 | Max parallel scenario executions |

### `async` (advanced, takes precedence)

| Field | Type | Default | Description |
|---|---|---|---|
| `num_workers` | int | 8 | Worker pool size |
| `arrival_rate_per_sec` | float | 20.0 | Scenario arrival rate |
| `exec_rate_per_min` | int | 100 | Max executions per minute |
| `max_retries` | int | 3 | Retry attempts on transient failure |
| `task_timeout_seconds` | int | 300 | Timeout per scenario (5 min) |
| `stuck_timeout_seconds` | int | 600 | Global stuck detection timeout |
| `emit_progress_interval_sec` | int | 10 | Progress log interval |

### `conversational` (required for conv evals)

| Field | Type | Default | Description |
|---|---|---|---|
| `max_turns` | int | 10 | Maximum conversation turns |
| `max_turn_length` | int | 2000 | Max characters per turn |
| `max_duration_ms` | int | 300000 | Max conversation duration (5 min) |
| `turn_generator.model_id` | string | — | Model key for the turn generator |
| `turn_generator.temperature` | float | 0.0 | Turn generator temperature |
| `turn_generator.max_tokens` | int | 500 | Max tokens per generated turn |
| `elaboration.enabled` | bool | false | Enable turn elaboration |

---

## `agents.json`

No strict top-level Pydantic model. Validated ad-hoc.

### `_models` section

Each key under `_models` is a **model ID** referenced by `eval_config.json "variants"` and by agent entries.

| Field | Type | Required | Description |
|---|---|---|---|
| `model_provider` | `"anthropic" \| "openai" \| "vertex_ai" \| "ollama" \| "bedrock"` | Yes | Provider |
| `model_family` | `"claude" \| "gpt" \| "gemini" \| "qwen"` | Yes | Used for DeepEval model routing |
| `model_version` | string | Yes | Provider-specific model ID (e.g., `"claude-haiku-4-5-20251001"`) |
| `model_parameters.temperature` | float | No | Default: 0.7 |
| `model_parameters.max_tokens` | int | No | Default: 4096 |
| `model_parameters.top_p` | float | No | Default: 1.0 |
| `provider_auth.api_key` | string | Cond. | API key or `"{{ENV_VAR}}"` / `"${ENV_VAR}"` template |
| `provider_auth.base_url` | string | Ollama | Required for Ollama (`"http://localhost:11434"`) |

**Note on API key resolution**: `{{ANTHROPIC_API_KEY}}` and `${ANTHROPIC_API_KEY}` templates
ARE auto-resolved from environment variables in DeepEval judge model creation. However,
the main LLM call path does NOT auto-resolve them — set real keys or environment variables directly.

### Agent entries (non-`_models`)

Used for conversational turn generators and judge model resolution.

| Field | Type | Required | Description |
|---|---|---|---|
| `model_id` | string | Yes | Key into `_models` |
| `prompt` | string | Yes | `"prompt-name:v1"` or `"prompt-name:latest"` |
| `model_parameters` | object | No | Overrides for this agent |
| `custom_configs` | object | No | Arbitrary agent-specific config |

---

## `prompts/{name}.toml`

```toml
v1 = '''
System prompt text here.
Use {{input}} for scenario input substitution.
'''

v2 = '''
Updated prompt text.
'''
```

**Rules:**
- Version keys must be `v1`, `v2`, … (sequential integers, no gaps)
- Reference format in `agents.json`: `"prompt-name:v1"` or `"prompt-name:latest"`
- `"latest"` resolves to the highest numbered version at runtime
- `{{input}}` is the standard variable for scenario `input` field injection
- Prompts are TOML triple-quoted strings — avoid unescaped triple quotes in content

---

## Key Cross-File Relationships

```
eval_config.json variants[]          →  agents.json _models keys
eval_config.json test_subjects[].prompt_name  →  prompts/{name}.toml
eval_config.json judges[].config.model        →  agents.json _models keys
agents.json agent.model_id           →  agents.json _models keys
```

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| `eval_config.json` references a model key not in `agents.json._models` | Add the model entry to `_models` |
| `variants` list contains a key not in `_models` | Match variant names exactly to `_models` keys |
| Prompt version gap (e.g., v1, v3) | Rename to sequential versions |
| `{{ENV_VAR}}` in api_key not resolving for main LLM calls | Export the env var or hardcode the key (dev only) |
| `execution` and `async` both set | Remove `execution`; `async` takes precedence |
| `conversational` section missing for conv eval | Add the full `conversational` block to `eval_config.json` |
