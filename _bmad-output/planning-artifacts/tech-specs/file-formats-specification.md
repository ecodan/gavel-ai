# File Formats Specification

**Version:** 1.0
**Created:** 2026-01-10
**Status:** Implementation Specification
**Derives From:** [data-schemas-specification.md](./data-schemas-specification.md) (Source of Truth)

---

## Overview

This document defines how gavel-ai data schemas serialize to **file formats** for local filesystem storage.

**This is an implementation detail.** The pure data schemas (source of truth) are defined in `data-schemas-specification.md`.

This specification covers:
- JSON/JSONL/TOML file formats
- Directory structure conventions
- File naming conventions
- Serialization rules for schemas → files

### File Categories

1. **Configuration Files** (Input - Read-Only during run)
   - `eval_config.json` - Evaluation configuration
   - `agents.json` - Agent and model definitions
   - `prompts/*.toml` - Prompt templates (versioned)
   - `scenarios.json` - Test scenarios
   - `judges/*.json` - Custom judge configurations (optional)

2. **Run Artifacts** (Output - Written during run)
   - `results_raw.jsonl` - Raw processor outputs
   - `results_judged.jsonl` - Processor outputs + judge evaluations
   - `run_metadata.json` - Run statistics and telemetry
   - `manifest.json` - Run manifest for reproducibility
   - `report.html` - Human-readable report
   - `telemetry.jsonl` - OpenTelemetry spans (optional)

---

## 1. Configuration Files (Input)

### 1.1 eval_config.json

**Location:** `.gavel/evaluations/{eval_name}/config/eval_config.json`

**Purpose:** Primary evaluation configuration defining what to test and how.

**Data Schema:** See [EvalConfig](./data-schemas-specification.md#11-evalconfig) for field definitions

**File Format - JSON:**

```json
{
  "eval_type": "oneshot | conversational | autotune",
  "eval_name": "string",
  "description": "string (optional)",
  "test_subject_type": "local | remote",
  "test_subjects": [
    {
      "prompt_name": "string (for local type)",
      "system_id": "string (for remote type, optional)",
      "protocol": "acp | open_ai (for remote type, optional)",
      "config": {
        "key": "value (for remote type, optional)"
      },
      "judges": [
        {
          "name": "string (unique judge identifier)",
          "type": "deepeval.similarity | deepeval.geval | custom.{name}",
          "config": {
            "model": "string (LLM model ID from agents.json)",
            "criteria": "string (for GEval)",
            "evaluation_steps": ["string"] "(for GEval)",
            "threshold": "float 0.0-1.0 (optional)",
            "...": "judge-specific config"
          },
          "config_ref": "string (path to external config, optional)",
          "threshold": "float 0.0-1.0 (optional)",
          "model": "string (shorthand for config.model, optional)"
        }
      ]
    }
  ],
  "variants": ["string (model IDs from agents.json._models)"],
  "scenarios": {
    "source": "file.local | file.remote | generator",
    "name": "string (filename or generator name)"
  },
  "execution": {
    "max_concurrent": "integer (default: 5)"
  },
  "async": {
    "num_workers": "integer (default: 8)",
    "arrival_rate_per_sec": "float (default: 20.0)",
    "exec_rate_per_min": "integer (default: 100)",
    "max_retries": "integer (default: 3)",
    "task_timeout_seconds": "integer (default: 300)",
    "stuck_timeout_seconds": "integer (default: 600)",
    "emit_progress_interval_sec": "integer (default: 10)"
  }
}
```

**Field Descriptions:**

- `eval_type`: Type of evaluation workflow
- `eval_name`: Unique evaluation identifier
- `test_subject_type`: Whether testing local prompts or remote systems
- `test_subjects[]`: List of things to test (prompts or remote systems)
  - `prompt_name`: Reference to prompt in `prompts/{name}.toml` (local only)
  - `judges[]`: Judges to evaluate this test subject
    - `name`: Unique judge ID for this evaluation
    - `type`: Judge implementation type
    - `config`: Judge-specific configuration (varies by type)
- `variants[]`: Model IDs to test (must exist in agents.json._models)
- `scenarios`: Where to load test scenarios from
- `execution`: Synchronous execution settings
- `async`: Asynchronous execution settings (overrides execution if present)

**Example:**

```json
{
  "eval_type": "oneshot",
  "test_subject_type": "local",
  "eval_name": "assistant_quality",
  "description": "Evaluate assistant response quality",
  "test_subjects": [
    {
      "prompt_name": "assistant",
      "judges": [
        {
          "name": "quality",
          "type": "deepeval.geval",
          "config": {
            "model": "gpt-5-mini",
            "criteria": "Evaluate the quality and accuracy of the response",
            "evaluation_steps": [
              "Check if the response is accurate",
              "Verify completeness of answer",
              "Assess clarity and usefulness"
            ]
          }
        }
      ]
    }
  ],
  "variants": ["claude_haiku", "gpt_5_mini"],
  "scenarios": {
    "source": "file.local",
    "name": "scenarios.json"
  },
  "async": {
    "num_workers": 8,
    "arrival_rate_per_sec": 20.0,
    "max_retries": 3
  }
}
```

---

### 1.2 agents.json

**Location:** `.gavel/evaluations/{eval_name}/config/agents.json`

**Purpose:** Model and agent definitions. Defines base models and agent configurations that use those models.

**Data Schema:** See [AgentsConfig](./data-schemas-specification.md#17-agentsconfig) for field definitions

**File Format - JSON:**

```json
{
  "_models": {
    "{model_id}": {
      "model_provider": "anthropic | openai | vertex_ai | ollama | bedrock",
      "model_family": "claude | gpt | gemini | qwen | ...",
      "model_version": "string (specific model version)",
      "model_parameters": {
        "temperature": "float 0.0-2.0 (optional)",
        "max_tokens": "integer (optional)",
        "top_p": "float 0.0-1.0 (optional)",
        "...": "provider-specific parameters"
      },
      "provider_auth": {
        "api_key": "string or {{ENV_VAR}}",
        "base_url": "string (optional, for custom endpoints)",
        "...": "provider-specific auth"
      }
    }
  },
  "{agent_name}": {
    "model_id": "string (reference to _models key)",
    "prompt": "string (prompt_name:version, e.g., 'assistant:v1')",
    "model_parameters": {
      "...": "optional model parameter overrides"
    },
    "custom_configs": {
      "...": "optional agent-specific config"
    }
  }
}
```

**Field Descriptions:**

- `_models`: Dictionary of base model configurations
  - Key: model_id (referenced by variants and judge configs)
  - `model_provider`: Which AI provider to use
  - `model_family`: Model family/type
  - `model_version`: Specific model version string
  - `model_parameters`: Model invocation parameters
  - `provider_auth`: Authentication configuration (supports {{ENV_VAR}} interpolation)
- `{agent_name}`: Named agent configurations (optional)
  - `model_id`: Which model from `_models` to use
  - `prompt`: Prompt template reference
  - `model_parameters`: Override base model parameters
  - `custom_configs`: Custom agent configuration

**Example:**

```json
{
  "_models": {
    "claude_haiku": {
      "model_provider": "anthropic",
      "model_family": "claude",
      "model_version": "claude-haiku-4-5-20251001",
      "model_parameters": {
        "temperature": 0.3,
        "max_tokens": 4096
      },
      "provider_auth": {
        "api_key": "{{ANTHROPIC_API_KEY}}"
      }
    },
    "gpt_5_mini": {
      "model_provider": "openai",
      "model_family": "gpt",
      "model_version": "gpt-5-mini-2025-08-07",
      "model_parameters": {
        "temperature": 0.7,
        "max_tokens": 4096
      },
      "provider_auth": {
        "api_key": "{{OPENAI_API_KEY}}"
      }
    }
  },
  "assistant_agent": {
    "model_id": "claude_haiku",
    "prompt": "assistant:v1",
    "model_parameters": {
      "temperature": 0.5
    }
  }
}
```

---

### 1.3 prompts/{name}.toml

**Location:** `.gavel/evaluations/{eval_name}/config/prompts/{prompt_name}.toml`

**Purpose:** Versioned prompt templates with variable substitution.

**Schema:**

```toml
v1 = '''
Prompt template text here.
Can use {{variable_name}} for substitution.
'''

v2 = '''
Updated prompt template.
'''

# Latest version will be used by default when referenced as "name:latest"
```

**Field Descriptions:**

- Version keys (`v1`, `v2`, etc.): Sequential version identifiers
- Value: Prompt template text (multiline string)
- Variables: Use `{{variable_name}}` syntax for runtime substitution
  - Common variables: `{{input}}`, `{{context}}`, `{{expected}}`

**Example:**

```toml
v1 = '''
You are a helpful AI assistant.

User question: {{input}}

Provide a short, clear, accurate answer.
'''

v2 = '''
You are a helpful AI assistant designed to provide accurate, concise answers.

User question: {{input}}
{{#if expected}}Expected behavior: {{expected}}{{/if}}

Provide a short, clear, accurate answer.
'''
```

---

### 1.4 scenarios.json

**Location:** `.gavel/evaluations/{eval_name}/config/scenarios.json`

**Purpose:** Test scenarios with inputs and optional expected behavior.

**Schema:**

```json
[
  {
    "id": "string (unique scenario identifier)",
    "input": "string or dict (scenario input data)",
    "expected_behavior": "string (optional - expected output or behavior)",
    "metadata": {
      "key": "value (optional scenario metadata)"
    }
  }
]
```

**Field Descriptions:**

- `id`: Unique scenario identifier (required)
- `input`: Input data for the scenario
  - Can be a string (simple input) or dict (structured input)
- `expected_behavior`: Expected output or behavior (optional)
  - Used by judges for evaluation
  - Alias: can also use `expected` field name
- `metadata`: Optional metadata (tags, categories, etc.)

**Example:**

```json
[
  {
    "id": "greeting_01",
    "input": "Hello, how are you?",
    "expected_behavior": "Polite greeting response",
    "metadata": {
      "category": "greetings",
      "difficulty": "easy"
    }
  },
  {
    "id": "math_01",
    "input": {
      "question": "What is 15 * 23?",
      "show_work": true
    },
    "expected_behavior": "345 with calculation steps shown"
  }
]
```

**Alternative Format - CSV:**

Scenarios can also be provided as `scenarios.csv`:

```csv
id,input,expected_behavior,metadata
greeting_01,"Hello, how are you?",Polite greeting response,"{""category"": ""greetings""}"
math_01,"What is 15 * 23?",345,"{""category"": ""math""}"
```

---

### 1.5 judges/{name}.json

**Location:** `.gavel/evaluations/{eval_name}/config/judges/{judge_name}.json` (optional)

**Purpose:** External judge configuration files (referenced by config_ref).

**Schema:**

```json
{
  "type": "deepeval.geval | custom.{name}",
  "config": {
    "model": "string (model ID)",
    "criteria": "string",
    "evaluation_steps": ["string"],
    "threshold": "float 0.0-1.0",
    "...": "judge-specific configuration"
  }
}
```

**Usage:** Referenced from eval_config.json via `config_ref` field.

---

## 2. Run Artifacts (Output)

### 2.1 results_raw.jsonl

**Location:** `.gavel/evaluations/{eval_name}/runs/{run_id}/results_raw.jsonl`

**Purpose:** Immutable record of processor execution. Each line is a JSON object representing one scenario execution.

**Data Schema:** See [OutputRecord](./data-schemas-specification.md#21-outputrecord) for field definitions

**File Format - JSONL (one JSON object per line):**

```json
{
  "test_subject": "string (prompt name or system ID)",
  "variant_id": "string (model ID from agents.json)",
  "scenario_id": "string (scenario.id)",
  "processor_output": "string (output from model/system)",
  "timing_ms": "integer (execution time in milliseconds)",
  "tokens_prompt": "integer (prompt tokens used)",
  "tokens_completion": "integer (completion tokens generated)",
  "error": "string or null (error message if failed)",
  "timestamp": "string (ISO 8601 timestamp)"
}
```

**Field Descriptions:**

- `test_subject`: Which test subject was evaluated (prompt name or remote system ID)
- `variant_id`: Which model variant was used
- `scenario_id`: Which scenario was executed
- `processor_output`: Raw output from the processor/model
- `timing_ms`: Execution latency in milliseconds
- `tokens_prompt`: Number of prompt tokens consumed
- `tokens_completion`: Number of completion tokens generated
- `error`: Error message if execution failed (null if successful)
- `timestamp`: When this execution occurred (ISO 8601 format)

**Example:**

```jsonl
{"test_subject": "assistant", "variant_id": "claude_haiku", "scenario_id": "greeting_01", "processor_output": "Hello! I'm doing well, thank you for asking. How can I help you today?", "timing_ms": 1250, "tokens_prompt": 45, "tokens_completion": 22, "error": null, "timestamp": "2026-01-10T10:30:45.123Z"}
{"test_subject": "assistant", "variant_id": "claude_haiku", "scenario_id": "math_01", "processor_output": "15 * 23 = 345\n\nCalculation: 15 × 23 = (10 + 5) × 23 = 230 + 115 = 345", "timing_ms": 1580, "tokens_prompt": 52, "tokens_completion": 38, "error": null, "timestamp": "2026-01-10T10:30:46.500Z"}
```

**Characteristics:**

- **Immutable**: Never modified after creation
- **One line per scenario execution**: Easy to stream and process
- **No judge data**: Only processor execution results
- **Append-only**: Can be written incrementally during execution

---

### 2.2 results_judged.jsonl

**Location:** `.gavel/evaluations/{eval_name}/runs/{run_id}/results_judged.jsonl`

**Purpose:** Judge evaluations only. One row per test_subject + variant + scenario + judge. Must be joined with results_raw.jsonl for complete data.

**Data Schema:** See [JudgedRecord](./data-schemas-specification.md#22-judgedrecord) for field definitions

**File Format - JSONL (one JSON object per line):**

```json
{
  "test_subject": "string",
  "variant_id": "string",
  "scenario_id": "string",
  "judge_id": "string (judge name)",
  "score": "integer 1-10",
  "reasoning": "string or null (explanation)",
  "error": "string or null (error message if failed)",
  "timestamp": "string (ISO 8601)"
}
```

**Field Descriptions:**

- `test_subject`: Which test subject was evaluated (prompt name or remote system ID)
- `variant_id`: Which model variant was used
- `scenario_id`: Which scenario was executed
- `judge_id`: Judge name from eval_config.json
- `score`: Score from 1-10 (normalized scale)
- `reasoning`: Judge's explanation (null if error occurred)
- `error`: Error message if judging failed (null if successful)
- `timestamp`: When judge evaluation occurred

**Example:**

```jsonl
{"test_subject": "assistant", "variant_id": "claude_haiku", "scenario_id": "greeting_01", "judge_id": "quality", "score": 9, "reasoning": "Response is polite, appropriate, and offers assistance", "error": null, "timestamp": "2026-01-10T10:30:46.500Z"}
{"test_subject": "assistant", "variant_id": "claude_haiku", "scenario_id": "greeting_01", "judge_id": "accuracy", "score": 8, "reasoning": "Factually correct but could be more specific", "error": null, "timestamp": "2026-01-10T10:30:47.200Z"}
{"test_subject": "assistant", "variant_id": "gpt_5_mini", "scenario_id": "greeting_01", "judge_id": "quality", "score": 7, "reasoning": "Adequate but lacks warmth", "error": null, "timestamp": "2026-01-10T10:30:48.100Z"}
```

**Characteristics:**

- **Denormalized**: One line per judge evaluation (scenario with 2 variants × 3 judges = 6 lines)
- **Join required**: Must join with results_raw.jsonl on (test_subject, variant_id, scenario_id) for processor outputs
- **Re-judgeable**: Can be regenerated from results_raw + scenarios without re-running processor
- **Error handling**: If judging fails, score may be 0, error field populated, reasoning explains failure

---

### 2.3 run_metadata.json

**Location:** `.gavel/evaluations/{eval_name}/runs/{run_id}/run_metadata.json`

**Purpose:** Run statistics, telemetry, and execution summary.

**Data Schema:** See [RunMetadata](./data-schemas-specification.md#31-runmetadata) for field definitions

**File Format - JSON:**

```json
{
  "run_id": "string",
  "eval_name": "string",
  "start_time_iso": "string (ISO 8601)",
  "end_time_iso": "string (ISO 8601)",
  "total_duration_seconds": "float",
  "execution": {
    "completed": "integer",
    "failed": "integer",
    "retries": "integer",
    "retry_details": [
      {
        "scenario_id": "string",
        "attempt": "integer",
        "error": "string"
      }
    ]
  }
}
```

**Field Descriptions:**

- `run_id`: Unique run identifier
- `eval_name`: Evaluation name
- `start_time_iso` / `end_time_iso`: Run start/end timestamps
- `total_duration_seconds`: Total wall-clock time
- `execution`: Execution status summary
  - `completed`: Successfully completed scenarios
  - `failed`: Failed scenarios
  - `retries`: Number of retry attempts
  - `retry_details`: Details of retry attempts

**Example:**

```json
{
  "run_id": "run-20260110-103000",
  "eval_name": "assistant_quality",
  "start_time_iso": "2026-01-10T10:30:00.000Z",
  "end_time_iso": "2026-01-10T10:32:15.500Z",
  "total_duration_seconds": 135.5,
  "execution": {
    "completed": 50,
    "failed": 0,
    "retries": 2,
    "retry_details": [
      {
        "scenario_id": "math_05",
        "attempt": 2,
        "error": "Rate limit exceeded"
      }
    ]
  }
}
```

**Note on Detailed Metrics:**

This schema provides a **simplified execution summary**. Detailed performance metrics (scenario timing stats, LLM call counts, token usage by model, etc.) are available in `telemetry.jsonl` as the source of truth. Tools/reporters can aggregate telemetry data as needed.

---

### 2.5 report.html (and other formats)

**Location:** `.gavel/evaluations/{eval_name}/runs/{run_id}/report.{format}`

**Purpose:** Human-readable evaluation report.

**Formats:**

- `report.html` - HTML report with charts and tables
- `report.md` - Markdown report
- `report.pdf` - PDF report (optional)

**Content:** Generated from templates, includes:

- Run summary (metadata, duration, scenario count)
- Model comparison tables
- Judge score distributions
- Performance metrics (latency, tokens)
- Individual scenario results
- Charts and visualizations (HTML only)

**Schema:** Not applicable (template-generated, format-specific)

---

### 2.5 telemetry.jsonl

**Location:** `.gavel/evaluations/{eval_name}/runs/{run_id}/telemetry.jsonl`

**Purpose:** OpenTelemetry spans for LLM calls (local and distributed). **REQUIRED** for all runs.

**Schema:** OpenTelemetry JSON format (one span per line)

**Usage:**
- Tracing data for performance analysis and debugging
- For local runs, traces all LLM calls (processor + judge executions)
- Contains detailed timing, token counts, and execution metrics
- Source of truth for metrics aggregated in run_metadata.json

**Enforcement:**
- Every run MUST produce telemetry.jsonl
- RunContext should check for telemetry.jsonl after execution and **warn** (not fail) if missing
- Missing telemetry indicates instrumentation issue but doesn't invalidate run results 

---

## 3. File Organization

### Directory Structure

```
.gavel/
└── evaluations/
    └── {eval_name}/
        ├── config/
        │   ├── eval_config.json
        │   ├── agents.json
        │   ├── prompts/
        │   │   ├── {prompt_name}.toml
        │   │   └── ...
        │   └── judges/  (optional)
        │       ├── {judge_name}.json
        │       └── ...
        ├── data/        
        │   └── scenarios.json
        └── runs/
            └── {run_id}/
                ├── .config/  (snapshot of config/ for reproducibility)
                │   ├── eval_config.json
                │   ├── agents.json
                │   ├── prompts/
                │   │   └── ...
                │   └── judges/
                │       └── ...
                ├── results_raw.jsonl
                ├── results_judged.jsonl
                ├── run_metadata.json
                ├── report.html
                ├── report.md  (optional)
                ├── telemetry.jsonl
                └── run.log
```

### Config Snapshot

Each run creates a snapshot of the `config/` directory in the run directory. This ensures:

- **Reproducibility**: Exact configs used for this run are preserved
- **Immutability**: Config changes don't affect historical runs
- **Traceability**: Can verify config_hash against snapshotted files

---

## 4. Validation Rules

### Required Fields

All required fields must be present and non-null unless marked optional.

### Type Validation

- Strings: Non-empty unless explicitly allowed
- Integers: Must be integers (not floats)
- Floats: Can be floats or integers
- Arrays: Can be empty arrays unless specified otherwise
- Objects: Can be empty objects unless specified otherwise

### Cross-File Validation

1. **eval_config.json references**:
   - `variants[]` must exist in `agents.json._models`
   - `test_subjects[].prompt_name` must exist in `prompts/{name}.toml`
   - `test_subjects[].judges[].config.model` must exist in `agents.json._models`

2. **agents.json references**:
   - `{agent}.model_id` must exist in `_models`
   - `{agent}.prompt` format must be `{name}:{version}`

3. **scenarios references**:
   - `scenario.id` must be unique within scenarios array

### Score Normalization

All judge scores must be normalized to 1-10 integer scale for consistency across judge types.

---

## 5. Version History

| Version | Date       | Changes |
|---------|------------|---------|
| 1.0     | 2026-01-10 | Initial specification |

---

## 6. Schema Enforcement

Schemas are enforced via:

1. **Pydantic models** in `src/gavel_ai/core/config/models.py`
2. **Validation on load** via `ConfigLoader`
3. **Write-time validation** via data source classes

See:
- `src/gavel_ai/core/config/models.py` - Configuration schemas
- `src/gavel_ai/core/models.py` - Runtime data models
- `src/gavel_ai/telemetry/metadata.py` - Run metadata schema
- `src/gavel_ai/storage/results_exporter.py` - Results export schemas
