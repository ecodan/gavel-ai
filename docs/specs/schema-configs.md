# gavel-ai Configuration Schema Reference

This document describes all configuration file schemas used by gavel-ai evaluations.

---

## eval_config.json

Root evaluation configuration. Located at `config/eval_config.json` within the evaluation directory.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `eval_type` | `string` | required | Evaluation type; must be `"oneshot"` |
| `workflow_type` | `"oneshot" \| "conversational"` | `"oneshot"` | Evaluation workflow variant |
| `eval_name` | `string` | required | Evaluation identifier (matches directory name) |
| `description` | `string \| null` | `null` | Human-readable description |
| `test_subject_type` | `"local" \| "in-situ"` | required | Whether the subject is a local prompt or remote endpoint |
| `test_subjects` | `TestSubject[]` | required | One or more test subjects (see below) |
| `variants` | `string[]` | required | Agent/model variant IDs from `agents.json` |
| `scenarios` | `ScenariosConfig` | required | Scenario data source configuration |
| `execution` | `ExecutionConfig \| null` | `null` | Concurrency settings |
| `async` | `AsyncConfig \| null` | `null` | Async worker pool settings |
| `conversational` | `ConversationalConfig \| null` | `null` | Required when `workflow_type = "conversational"` |

### TestSubject

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prompt_name` | `string \| null` | `null` | Prompt template name (local subjects) |
| `judges` | `JudgeConfig[]` | required | Judges applied to this subject's outputs |
| `system_id` | `string \| null` | `null` | Remote system identifier (in-situ subjects) |
| `protocol` | `string \| null` | `null` | Remote protocol: `"open_ai"`, `"acp"` |
| `config` | `object \| null` | `null` | Remote system config (endpoint, model, etc.) |

### ScenariosConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | `string` | required | Data source type: `"file.local"` |
| `name` | `string` | required | Scenario file name (relative to `data/`) |
| `field_mapping` | `ScenarioFieldMapping \| null` | `null` | Maps scenario file fields to GEval test case params |

### ScenarioFieldMapping

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `input` | `string \| null` | `null` | Dot-notation path to input text in scenario |
| `expected_output` | `string \| null` | `null` | Dot-notation path to expected output |
| `actual_output` | `string \| null` | `null` | Dot-notation path to actual output (overrides processor output) |

### ExecutionConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_concurrent` | `integer` | `5` | Maximum concurrent scenario executions |

### AsyncConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `num_workers` | `integer` | `8` | Number of async worker tasks |
| `arrival_rate_per_sec` | `float` | `20.0` | Rate at which tasks are enqueued per second |
| `exec_rate_per_min` | `integer` | `100` | Maximum executions per minute |
| `max_retries` | `integer` | `3` | Retries per task on transient failure |
| `task_timeout_seconds` | `integer` | `300` | Per-task timeout in seconds |
| `stuck_timeout_seconds` | `integer` | `600` | Time before a stuck task is aborted |
| `emit_progress_interval_sec` | `integer` | `10` | Progress log interval in seconds |

### ConversationalConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_turns` | `integer` | `10` | Maximum conversation turns before termination |
| `max_turn_length` | `integer` | `2000` | Maximum characters per turn |
| `turn_generator` | `TurnGeneratorConfig` | required | Model used to generate user turns |
| `elaboration` | `ElaborationConfig \| null` | `null` | Optional scenario elaboration before execution |
| `max_duration_ms` | `integer` | `300000` | Hard timeout for the full conversation (ms) |
| `retry_config` | `RetryConfig \| null` | `RetryConfig()` | Retry settings for turn failures |

### TurnGeneratorConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model_id` | `string` | required | Model ID from `agents.json` for turn generation |
| `temperature` | `float` | `0.0` | Sampling temperature (0 = deterministic) |
| `max_tokens` | `integer` | `500` | Max tokens per generated turn |

---

## agents.json

Agent and model configuration. Located at `config/agents.json`.

### _models section

Each key under `_models` defines a reusable model configuration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model_provider` | `string` | required | Provider: `"anthropic"`, `"openai"`, `"ollama"`, `"vertex_ai"` |
| `model_family` | `string` | required | Family: `"claude"`, `"gpt"`, `"gemini"`, `"qwen"` |
| `model_version` | `string` | required | Full model version string (e.g. `"claude-haiku-4-5-20251001"`) |
| `model_parameters` | `object` | `{}` | Provider parameters: `temperature`, `max_tokens`, etc. |
| `provider_auth` | `object` | `{}` | Auth config: `api_key` (supports `{{ENV_VAR}}` expansion) or `base_url` |

### Agent entries

Each non-`_models` key is an agent that references a model.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `model_id` | `string` | required | Key in `_models` to use |
| `prompt` | `string` | required | Prompt reference: `"name:version"` or `"name:latest"` |
| `model_parameters` | `object \| null` | `null` | Override model-level parameters for this agent |
| `custom_configs` | `object \| null` | `null` | Agent-specific custom settings (e.g., logging) |

**Example:**
```json
{
  "_models": {
    "claude-haiku": {
      "model_provider": "anthropic",
      "model_family": "claude",
      "model_version": "claude-haiku-4-5-20251001",
      "model_parameters": {"temperature": 0.3, "max_tokens": 4096},
      "provider_auth": {"api_key": "{{ANTHROPIC_API_KEY}}"}
    }
  },
  "my_agent": {
    "model_id": "claude-haiku",
    "prompt": "assistant:v1"
  }
}
```

---

## scenarios.json

Test scenario data. Located at `data/{scenarios.name}`. Each element in the JSON array is a scenario.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `scenario_id` / `id` | `string` | required | Unique scenario identifier |
| `input` | `string \| object` | required | Input to the model: plain string or structured dict |
| `expected` / `expected_behavior` | `string \| null` | `null` | Expected output string (used by GEval judges) |
| `expected_output` | `any \| null` | `null` | Structured expected output (for field_mapping use) |
| `context` | `string \| null` | `null` | Context string for retrieval-based judges |
| `metadata` | `object` | `{}` | Arbitrary key-value pairs for field resolution and templating |

**Notes:**
- Both `scenario_id` and `id` are accepted (aliases).
- Both `expected` and `expected_behavior` are accepted (aliases).
- `input` as a dict enables dot-notation field resolution in `field_mapping` and `{{key}}` template substitution.

---

## Judge Config Fields

Judges are configured inline within `test_subjects[].judges[]` in `eval_config.json`, or referenced via `config_ref` to a TOML file at `config/judges/{name}.toml`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `string` | required | Judge identifier (used in output records) |
| `type` | `string` | required | Judge type (see types below) |
| `threshold` | `float \| null` | `null` | Pass/fail threshold (0.0–1.0); type-specific defaults apply |
| `model` | `string \| null` | `null` | LLM model ID for judge evaluation |
| `config` | `object \| null` | `null` | Judge-specific nested config dict |
| `config_ref` | `string \| null` | `null` | Name of TOML file in `config/judges/` (without `.toml`) |
| `markdown_path` | `string \| null` | `null` | Path (relative to eval dir) of a Markdown config file |
| `criteria` | `string \| null` | `null` | GEval evaluation criteria (supports `{{key}}` templating) |
| `evaluation_steps` | `string[] \| null` | `null` | GEval evaluation steps (each supports `{{key}}` templating) |

### Judge Types

| Type | Class | Notes |
|------|-------|-------|
| `deepeval.answer_relevancy` | `AnswerRelevancyMetric` | Requires `threshold`; optional `model` |
| `deepeval.contextual_relevancy` | `ContextualRelevancyMetric` | Requires `threshold`; optional `model` |
| `deepeval.faithfulness` | `FaithfulnessMetric` | Recommended threshold: 0.65–0.80 |
| `deepeval.hallucination` | `HallucinationMetric` | Recommended threshold: 0.85–0.95 |
| `deepeval.geval` | `GEval` | Requires `model`, `criteria`, `evaluation_steps` in `config` |
| `deepeval.toxicity` | `ToxicityMetric` | Recommended threshold: 0.85–0.95 |
| `deepeval.conversation_completeness` | `ConversationCompletenessMetric` | Recommended threshold: 0.70–0.85 |
| `deepeval.conversational_geval` | `ConversationalGEval` | Requires `model`, `criteria`, `evaluation_steps` in `config` |
| `deepeval.turn_relevancy` | `TurnRelevancyMetric` | Conversational turn-level relevancy |
| `classifier` | `ClassifierMetric` | Deterministic; requires `prediction_field`, `actual_field` |
| `regression` | `RegressionMetric` | Deterministic; requires `prediction_field`, `actual_field` |

### Markdown Judge Config Format

When `markdown_path` is set, the file is parsed for these sections (h2 headings):

```markdown
## Criteria
Your evaluation criteria text here.

## Evaluation Steps
- Step one
- Step two

## Threshold
0.75

## Guidelines
Additional guidance for the judge.
```

Missing sections are silently ignored. Parsed values are merged into the judge config; `config_ref` values take precedence over markdown values.

### Criteria Templating

`criteria` and `evaluation_steps` support `{{key}}` substitution using scenario context:
- Dict `input` fields are unpacked: `{{field_name}}`
- String `input` is available as `{{input}}`
- `metadata` keys are merged in: `{{metadata_key}}`
- Unknown placeholders pass through unchanged.

### ClassifierMetric config

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prediction_field` | `string` | `"prediction"` | Dot-notation path in JSON processor output |
| `actual_field` | `string` | `"actual"` | Dot-notation path in scenario (input dict or scenario fields) |
| `report_metric` | `string` | `"accuracy"` | scikit-learn metric: `"accuracy"`, `"f1"`, `"fbeta"` |
| `beta` | `float` | `1.0` | Beta for fbeta; required when `report_metric = "fbeta"` |

### RegressionMetric config

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `prediction_field` | `string` | `"prediction"` | Dot-notation path in JSON processor output |
| `actual_field` | `string` | `"actual"` | Dot-notation path in scenario |
| `report_metric` | `string` | `"accuracy"` | scikit-learn metric: `"mean_absolute_error"`, `"mean_squared_error"`, `"r2_score"` |
