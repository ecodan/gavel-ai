# Data Schemas Specification

**Version:** 1.0
**Created:** 2026-01-10
**Status:** Source of Truth

---

## Overview

This document defines the **pure data models** for gavel-ai, independent of storage implementation (files, APIs, databases, etc.).

All implementation-specific formats (JSON, JSONL, TOML, SQL, etc.) derive from these schemas.

### Schema Categories

1. **Configuration Schemas** - Input data defining evaluations
2. **Execution Result Schemas** - Output data from runs
3. **Metadata Schemas** - Run statistics and telemetry
4. **Domain Models** - Core business entities

---

## 1. Configuration Schemas

### 1.1 EvalConfig

**Purpose:** Primary evaluation configuration defining what to test and how.

**Schema:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `eval_type` | string | Yes | enum: oneshot, conversational, autotune | Evaluation workflow type |
| `eval_name` | string | Yes | non-empty, unique | Evaluation identifier |
| `description` | string | No | - | Human-readable description |
| `test_subject_type` | string | Yes | enum: local, remote | Whether testing local prompts or remote systems |
| `test_subjects` | TestSubject[] | Yes | min length: 1 | List of subjects to evaluate |
| `variants` | string[] | Yes | min length: 1 | Model variant IDs (must exist in AgentsConfig._models) |
| `scenarios` | ScenariosConfig | Yes | - | Scenario source configuration |
| `execution` | ExecutionConfig | No | - | Synchronous execution settings |
| `async_config` | AsyncConfig | No | - | Asynchronous execution settings (overrides execution) |

**Validation Rules:**

1. `variants[]` elements must exist as keys in `AgentsConfig._models`
2. If `test_subject_type == "local"`, each `test_subjects[].prompt_name` must be non-null
3. If `test_subject_type == "remote"`, each `test_subjects[].system_id` must be non-null
4. `test_subjects[].judges[].name` must be unique within each test subject
5. If `async_config` present, `execution` settings are ignored

---

### 1.2 TestSubject

**Purpose:** Defines a single system/prompt to test with associated judges.

**Schema:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `prompt_name` | string | Conditional | required if test_subject_type=="local" | Prompt template identifier |
| `judges` | JudgeConfig[] | Yes | - | Judges to evaluate this subject |
| `system_id` | string | Conditional | required if test_subject_type=="remote" | Remote system identifier |
| `protocol` | string | Conditional | enum: acp, open_ai (if remote) | Communication protocol for remote systems |
| `config` | dict | No | - | Remote system configuration |

**Validation Rules:**

1. If `prompt_name` provided, must reference valid prompt (name:version format)
2. `judges[].name` must be unique within this test subject
3. All `judges[].config.model` must exist in `AgentsConfig._models`

---

### 1.3 JudgeConfig

**Purpose:** Configuration for a single judge.

**Schema:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `name` | string | Yes | non-empty, unique per test subject | Judge identifier |
| `type` | string | Yes | format: {provider}.{judge_type} | Judge implementation (e.g., "deepeval.similarity") |
| `config` | dict | No | - | Judge-specific configuration |
| `config_ref` | string | No | - | Reference to external config |
| `threshold` | float | No | range: 0.0-1.0 | Pass/fail threshold |
| `model` | string | No | - | Shorthand for config.model |

**Common Config Fields (nested in `config`):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model` | string | Conditional | LLM model ID (for LLM-based judges) |
| `criteria` | string | Conditional | Evaluation criteria (for GEval) |
| `evaluation_steps` | string[] | Conditional | Evaluation steps (for GEval) |
| `threshold` | float | No | Judge-specific threshold override |

**Validation Rules:**

1. `type` must be registered judge implementation
2. If `config.model` specified, must exist in `AgentsConfig._models`
3. If `config_ref` provided, referenced config must exist
4. For GEval judges: `config.criteria` and `config.evaluation_steps` required

---

### 1.4 ScenariosConfig

**Purpose:** Defines where to load test scenarios.

**Schema:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `source` | string | Yes | enum: file.local, file.remote, generator | Scenario source type |
| `name` | string | Yes | non-empty | Filename or generator identifier |

---

### 1.5 ExecutionConfig

**Purpose:** Synchronous execution settings.

**Schema:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `max_concurrent` | integer | No | 5 | Maximum concurrent executions |

---

### 1.6 AsyncConfig

**Purpose:** Asynchronous execution settings (overrides ExecutionConfig).

**Schema:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `num_workers` | integer | No | 8 | Number of worker tasks |
| `arrival_rate_per_sec` | float | No | 20.0 | Task arrival rate per second |
| `exec_rate_per_min` | integer | No | 100 | Execution rate limit per minute |
| `max_retries` | integer | No | 3 | Maximum retry attempts |
| `task_timeout_seconds` | integer | No | 300 | Individual task timeout |
| `stuck_timeout_seconds` | integer | No | 600 | Stuck task timeout |
| `emit_progress_interval_sec` | integer | No | 10 | Progress reporting interval |

---

### 1.7 AgentsConfig

**Purpose:** Model and agent definitions.

**Schema:**

Top-level structure:
- `_models`: dict[string, ModelConfig] - Base model definitions (required)
- `{agent_name}`: AgentConfig - Named agent configurations (optional)

**ModelConfig:**

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `model_provider` | string | Yes | enum: anthropic, openai, vertex_ai, ollama, bedrock | AI provider |
| `model_family` | string | Yes | e.g., claude, gpt, gemini | Model family |
| `model_version` | string | Yes | provider-specific | Specific model version |
| `model_parameters` | dict | No | - | Model invocation parameters |
| `provider_auth` | dict | Yes | - | Authentication configuration |

**ModelConfig.model_parameters (common fields):**

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `temperature` | float | 0.0-2.0 | Sampling temperature |
| `max_tokens` | integer | > 0 | Maximum completion tokens |
| `top_p` | float | 0.0-1.0 | Nucleus sampling parameter |

**ModelConfig.provider_auth (common fields):**

| Field | Type | Description |
|-------|------|-------------|
| `api_key` | string | API key (supports {{ENV_VAR}} interpolation) |
| `base_url` | string | Custom endpoint URL (optional) |

**AgentConfig:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `model_id` | string | Yes | Reference to _models key |
| `prompt` | string | Yes | Prompt reference (format: name:version) |
| `model_parameters` | dict | No | Override base model parameters |
| `custom_configs` | dict | No | Agent-specific configuration |

**Validation Rules:**

1. All `variants[]` in EvalConfig must exist as keys in `_models`
2. All `AgentConfig.model_id` must exist in `_models`
3. All `JudgeConfig.config.model` must exist in `_models`
4. `AgentConfig.prompt` must match format `{name}:{version}` or `{name}:latest`

---

### 1.8 PromptTemplate

**Purpose:** Versioned prompt template with variable substitution.

**Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Prompt identifier |
| `versions` | dict[string, string] | Yes | Version keys (v1, v2, etc.) mapped to template text |

**Template Text:**
- Supports `{{variable_name}}` syntax for runtime substitution
- Common variables: `{{input}}`, `{{context}}`, `{{expected}}`

**Validation Rules:**

1. Version keys must match pattern: `v\d+` (e.g., v1, v2, v10)
2. At least one version required
3. Template text non-empty

---

### 1.9 Scenario

**Purpose:** Single test scenario with input and expected behavior.

**Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique scenario identifier |
| `input` | string \| dict | Yes | Scenario input (simple string or structured data) |
| `expected_behavior` | string | No | Expected output or behavior for judges |
| `metadata` | dict | No | Additional scenario metadata |

**Aliases:**
- `expected_behavior` can also be accessed as `expected`
- `id` can also be accessed as `scenario_id`

**Validation Rules:**

1. `id` must be unique within scenario collection
2. `input` must be non-empty

---

## 2. Execution Result Schemas

### 2.1 OutputRecord

**Purpose:** Single raw processor execution result.

**Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `test_subject` | string | Yes | Test subject identifier (prompt name or system ID) |
| `variant_id` | string | Yes | Model variant ID used for execution |
| `scenario_id` | string | Yes | Scenario identifier |
| `processor_output` | string | Yes | Raw output from processor/model |
| `timing_ms` | integer | Yes | Execution time in milliseconds |
| `tokens_prompt` | integer | Yes | Prompt tokens consumed |
| `tokens_completion` | integer | Yes | Completion tokens generated |
| `error` | string \| null | Yes | Error message if execution failed |
| `timestamp` | string | Yes | ISO 8601 timestamp of execution |

**Constraints:**
- `timing_ms` >= 0
- `tokens_prompt` >= 0
- `tokens_completion` >= 0
- `timestamp` must be valid ISO 8601 format

**Validation Rules:**

1. `test_subject` must match a test subject from EvalConfig
2. `variant_id` must exist in AgentsConfig._models
3. `scenario_id` must exist in scenario collection
4. If `error` is not null, execution failed

---

### 2.2 JudgedRecord

**Purpose:** Single judge evaluation result.

**Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `test_subject` | string | Yes | Test subject identifier |
| `variant_id` | string | Yes | Model variant ID |
| `scenario_id` | string | Yes | Scenario identifier |
| `judge_id` | string | Yes | Judge name from eval config |
| `score` | integer | Yes | Score from 1-10 (normalized scale) |
| `reasoning` | string \| null | Yes | Judge's explanation (null if error) |
| `error` | string \| null | Yes | Error message if judging failed |
| `timestamp` | string | Yes | ISO 8601 timestamp of evaluation |

**Constraints:**
- `score` range: 1-10 (inclusive)
- `timestamp` must be valid ISO 8601 format

**Relationship:**
- Joins with OutputRecord on (test_subject, variant_id, scenario_id)
- One-to-many: One OutputRecord can have multiple JudgedRecords (multiple judges)

**Validation Rules:**

1. `(test_subject, variant_id, scenario_id)` must exist in OutputRecord collection
2. `judge_id` must match a judge name from EvalConfig for this test_subject
3. If `error` is not null, judging failed and `reasoning` should be null

---

## 3. Metadata Schemas

### 3.1 RunMetadata

**Purpose:** Run execution summary and statistics.

**Schema:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `run_id` | string | Yes | Unique run identifier |
| `eval_name` | string | Yes | Evaluation name |
| `start_time_iso` | string | Yes | Run start timestamp (ISO 8601) |
| `end_time_iso` | string | Yes | Run end timestamp (ISO 8601) |
| `total_duration_seconds` | float | Yes | Total wall-clock run time |
| `execution` | ExecutionSummary | Yes | Execution status summary |

**ExecutionSummary:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `completed` | integer | Yes | Successfully completed scenarios |
| `failed` | integer | Yes | Failed scenarios |
| `retries` | integer | Yes | Total number of retry attempts |
| `retry_details` | RetryDetail[] | Yes | Details of retry attempts |

**RetryDetail:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scenario_id` | string | Yes | Scenario that was retried |
| `attempt` | integer | Yes | Attempt number |
| `error` | string | Yes | Error that triggered retry |

**Constraints:**
- `total_duration_seconds` >= 0
- `completed` >= 0
- `failed` >= 0
- `retries` >= 0
- `start_time_iso` < `end_time_iso`

**Note on Detailed Metrics:**

This schema provides a minimal execution summary. Detailed performance metrics (scenario timing distributions, LLM call counts, token usage by model, etc.) are derived from telemetry data (TelemetrySpan records).

---

### 3.2 TelemetrySpan

**Purpose:** OpenTelemetry span for distributed tracing.

**Schema:**

OpenTelemetry OTLP/JSON format (industry standard).

**Key Fields (subset relevant to gavel-ai):**

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | string | Trace identifier |
| `span_id` | string | Span identifier |
| `parent_span_id` | string \| null | Parent span ID (null for root spans) |
| `name` | string | Span name (e.g., "llm_call", "judge_evaluation") |
| `start_time` | integer | Start time in nanoseconds |
| `end_time` | integer | End time in nanoseconds |
| `attributes` | dict | Span attributes (model, tokens, etc.) |
| `status` | object | Span status (ok, error) |

**Common Attributes for LLM Calls:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `llm.model` | string | Model identifier |
| `llm.tokens.prompt` | integer | Prompt tokens |
| `llm.tokens.completion` | integer | Completion tokens |
| `scenario.id` | string | Associated scenario ID |
| `variant.id` | string | Model variant ID |

**Usage:**
- Source of truth for detailed performance metrics
- Aggregated to produce timing statistics, token counts, call distributions
- Required for all runs (warn if missing)

---

## 4. Cross-Schema Relationships

### 4.1 Reference Integrity

**EvalConfig → AgentsConfig:**
- `EvalConfig.variants[]` → `AgentsConfig._models[key]`
- `EvalConfig.test_subjects[].judges[].config.model` → `AgentsConfig._models[key]`

**EvalConfig → PromptTemplate:**
- `EvalConfig.test_subjects[].prompt_name` → `PromptTemplate.name`

**EvalConfig → Scenario:**
- References scenario collection via `ScenariosConfig`

**AgentsConfig → PromptTemplate:**
- `AgentsConfig.{agent}.prompt` → `PromptTemplate.name:version`

**OutputRecord → EvalConfig:**
- `OutputRecord.test_subject` → `EvalConfig.test_subjects[].prompt_name` or `system_id`
- `OutputRecord.variant_id` → `EvalConfig.variants[]`

**OutputRecord → Scenario:**
- `OutputRecord.scenario_id` → `Scenario.id`

**JudgedRecord → OutputRecord:**
- Join on: `(test_subject, variant_id, scenario_id)`
- Relationship: One OutputRecord → Many JudgedRecords (one per judge)

**JudgedRecord → EvalConfig:**
- `JudgedRecord.judge_id` → `EvalConfig.test_subjects[].judges[].name`

### 4.2 Cardinality

**Per Run:**
- 1 EvalConfig
- 1 AgentsConfig
- N Scenarios
- N × M OutputRecords (N scenarios × M variants)
- N × M × J JudgedRecords (N scenarios × M variants × J judges per subject)
- 1 RunMetadata
- K TelemetrySpans (variable, includes all LLM calls + judge evaluations)

**Example:**
- 50 scenarios × 2 variants = 100 OutputRecords
- 50 scenarios × 2 variants × 3 judges = 300 JudgedRecords

---

## 5. Validation Rules Summary

### 5.1 Type Validation

- **Strings**: Non-empty unless explicitly nullable
- **Integers**: Must be integers (not floats), >= 0 unless specified
- **Floats**: Can be floats or integers, >= 0.0 unless specified
- **Arrays**: Can be empty unless minimum length specified
- **Dicts**: Can be empty unless required fields specified
- **Enums**: Must match one of allowed values exactly

### 5.2 Format Validation

- **ISO 8601 timestamps**: Must parse as valid ISO 8601
- **Prompt references**: Must match `{name}:{version}` or `{name}:latest`
- **Environment variables**: `{{ENV_VAR}}` pattern in strings
- **Score normalization**: All judge scores normalized to 1-10 integer scale

### 5.3 Business Rules

1. **Unique identifiers**:
   - `Scenario.id` unique within scenario collection
   - `JudgeConfig.name` unique within test subject
   - `AgentsConfig._models` keys globally unique

2. **Reference integrity**: All foreign key references must resolve

3. **Conditional requirements**:
   - `test_subject_type=="local"` requires `prompt_name`
   - `test_subject_type=="remote"` requires `system_id`
   - GEval judges require `criteria` and `evaluation_steps`

4. **Normalized scores**: Judge scores 1-10 regardless of source judge scale

---

## 6. Extension Points

### 6.1 Custom Judge Types

New judge types can be registered by:
1. Implementing judge interface
2. Registering type string (format: `{provider}.{type}`)
3. Defining required `config` fields
4. Ensuring output scores normalized to 1-10

### 6.2 Custom Test Subject Types

Future support for additional test subject types:
- Current: `local` (prompts), `remote` (closed-box systems)
- Potential: `agent` (multi-turn agents), `pipeline` (multi-stage systems)

### 6.3 Custom Metadata

- `Scenario.metadata`: Arbitrary key-value pairs
- `AgentsConfig.{agent}.custom_configs`: Agent-specific configuration
- `TelemetrySpan.attributes`: Custom telemetry attributes

---

## 7. Schema Versioning

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-10 | Initial specification |

**Compatibility Policy:**

- **Backward compatible changes**: Add optional fields, relax constraints
- **Breaking changes**: Require major version bump, migration guide
- **Deprecation**: Mark fields as deprecated, provide sunset timeline

---

## 8. Implementation Notes

### 8.1 Pydantic Models

Schemas enforced via Pydantic models in:
- `src/gavel_ai/core/config/models.py` - Configuration schemas
- `src/gavel_ai/core/models.py` - Execution result schemas
- `src/gavel_ai/telemetry/metadata.py` - Metadata schemas

### 8.2 Serialization Formats

These schemas can serialize to:
- **JSON**: For configuration files, single-record storage
- **JSONL**: For record streams (OutputRecord, JudgedRecord, TelemetrySpan)
- **TOML**: For versioned templates (PromptTemplate)
- **CSV**: For scenarios (simplified format)
- **Parquet**: For analytics/archival (future)
- **SQL**: For queryable storage (future)
- **API Responses**: REST/GraphQL (future)

See `file-formats-specification.md` for file-specific serialization details.

### 8.3 Storage Abstraction

Data sources abstract storage location:
- `StructDataSource`: Single structured records (EvalConfig, RunMetadata)
- `RecordDataSource`: Collections of records (OutputRecord, JudgedRecord)
- `TextDataSource`: Unstructured text (logs, reports)

Storage backends abstract physical storage:
- `LocalStorageBackend`: Filesystem
- `S3StorageBackend`: S3/compatible object storage
- `HTTPStorageBackend`: Remote HTTP APIs (future)
- `DatabaseStorageBackend`: SQL/NoSQL databases (future)

---

## 9. Design Principles

1. **Storage-agnostic**: Schemas independent of serialization format
2. **Normalized scores**: All judges use 1-10 scale for comparability
3. **Immutable results**: OutputRecord never modified after creation
4. **Re-judgeable**: JudgedRecords regenerable from OutputRecord + Scenario
5. **Traceable**: TelemetrySpan provides full execution audit trail
6. **Extensible**: Custom judges, metadata, attributes supported
7. **Type-safe**: Strong typing enforced via Pydantic models
8. **Reference integrity**: Foreign keys validated across schemas
