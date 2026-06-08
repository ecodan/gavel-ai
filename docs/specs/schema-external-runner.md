# External Runner Protocol — Schema Reference

This document describes all payload shapes exchanged between the gavel-ai evaluation engine
and external systems under test (SUT) or external judges over the two supported transports:
**HTTP** and **script** (subprocess + temp-dir file handoff).

For configuration schema (how to declare an external test subject), see
[schema-configs.md](schema-configs.md). For run output schemas (results_raw.jsonl,
results_judged.jsonl, telemetry), see [schema-outputs.md](schema-outputs.md).

---

## Transport Model and Schema Sharing

The gavel-ai external runner defines **three distinct Pydantic models** that cover all
eight transport-specific payload shapes:

| Shape | Transport | Direction | Model |
|-------|-----------|-----------|-------|
| HTTP task request | HTTP | Gavel → SUT | `ExternalTaskRequest` |
| HTTP task response | HTTP | SUT → Gavel | `ExternalResponseEnvelope` |
| HTTP judge request | HTTP | Gavel → judge | `ExternalJudgeRequest` |
| HTTP judge response | HTTP | judge → Gavel | `ExternalResponseEnvelope` |
| Script task request | script | written to `request.json` | `ExternalTaskRequest` |
| Script task response | script | read from `response.json` | `ExternalResponseEnvelope` |
| Script judge request | script | written to `request.json` | `ExternalJudgeRequest` |
| Script judge response | script | read from `response.json` | `ExternalResponseEnvelope` |

**Design rationale:** The payload contents are identical regardless of how they are delivered.
Only the delivery mechanism differs — HTTP sends the request as a POST body and reads the
JSON response body; script writes `request.json` to a temp directory and reads `response.json`
from that same directory after the subprocess exits. Using one model per logical role (task
request, judge request, response) avoids duplication and ensures consistency.

---

## Bound and Truncation Limits

The following fields have documented size limits. Callers **must** truncate before
constructing these models; the models themselves do not enforce truncation at the Pydantic
validation layer.

| Field | Model | Limit | Rationale |
|-------|-------|-------|-----------|
| `rendered_prompt` | `ExternalTaskRequest` | 32 KB | Prevents unbounded payload growth in high-scenario-count evals |
| `processor_output` | `ExternalJudgeRequest` | 32 KB | Same — judge input should be bounded |
| Script `stderr` captured by `ScriptInputProcessor` | (internal) | 4 096 chars | Stored in `metadata["stderr"]`; prevents runaway error capture |

---

## Schema Files

Generated JSON Schema files (Draft 2020-12) live in `docs/specs/schemas/`:

- [`schemas/external_task_request.json`](schemas/external_task_request.json)
- [`schemas/external_judge_request.json`](schemas/external_judge_request.json)
- [`schemas/external_response_envelope.json`](schemas/external_response_envelope.json)

Re-generate with:

```bash
uv run python scripts/generate_external_schemas.py
```

---

## 1. Task Request (HTTP + Script)

**Used by:** HTTP transport (POST body to the SUT endpoint) and script transport (written
as `request.json` in the subprocess temp directory).

**Pydantic model:** `gavel_ai.models.runtime.ExternalTaskRequest`

### Properties

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scenario_id` | `string` | yes | Scenario identifier from `scenarios.json` |
| `scenario_input` | `string \| object` | yes | Raw scenario input — may be a plain string or a structured JSON object, matching the scenario's `input` field |
| `rendered_prompt` | `string` | yes | Fully rendered prompt text ready for the SUT to consume (max 32 KB — see Truncation Limits) |
| `custom_config` | `object` | no (default `{}`) | Pass-through of `TestSubject.config` for SUT-specific settings (e.g. model name, temperature, endpoint-level flags) |
| `trace_id` | `string \| null` | no (default `null`) | Run-level trace identifier — correlates with `telemetry.jsonl` spans for the same run |
| `metadata` | `object` | no (default `{}`) | Additional per-invocation metadata (e.g. variant_id, run_id) |

### Example

```json
{
  "scenario_id": "greet-en-001",
  "scenario_input": "Hello, how are you?",
  "rendered_prompt": "You are a helpful assistant.\n\nUser: Hello, how are you?\nAssistant:",
  "custom_config": {
    "model": "llama3",
    "temperature": 0.2
  },
  "trace_id": "run-20240601-abc123",
  "metadata": {
    "variant_id": "llama3-v1"
  }
}
```

### Transport Notes

- **HTTP:** Sent as `Content-Type: application/json` POST body. The `trace_id` value is also
  injected as the `X-Gavel-Trace-Id` request header for transport-level correlation.
- **Script:** Written as UTF-8 JSON to `{tmpdir}/request.json` before subprocess launch.
  The filename is configurable via `TestSubject.config.request_filename` (default `request.json`).

---

## 2. Task Response (HTTP + Script)

**Used by:** HTTP transport (JSON response body from the SUT) and script transport (read as
`response.json` from the subprocess temp directory after the process exits).

**Pydantic model:** `gavel_ai.models.runtime.ExternalResponseEnvelope`

### Properties

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | `"ok" \| "error"` | yes | Top-level outcome. `"ok"` = success (possibly with an attached `issue`); `"error"` = the SUT self-reported failure |
| `result` | `object \| null` | no (default `null`) | Task output content. Callers should use `result.output` (string) as the primary processor output; additional fields are passed through in `metadata` |
| `metadata` | `object` | no (default `{}`) | SUT-reported timing and custom fields (e.g. `timing_ms`, `tokens`, `model`) |
| `issue` | `ExternalIssue \| null` | no (default `null`) | Structured error/warning when the SUT encountered an internal problem. Present even when `status: "ok"` for `PROCESS_SUCCESS_WITH_ISSUE` tier |
| `trace_id` | `string \| null` | no (default `null`) | Echo of the inbound `trace_id` for debugging on the SUT side |

### ExternalIssue Sub-schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | `string` | yes | Stable, documented issue code (e.g. `"low_confidence"`, `"quota_warning"`) |
| `level` | `"error" \| "warning"` | yes | Issue severity. `"warning"` → `PROCESS_SUCCESS_WITH_ISSUE` tier; `"error"` → same |
| `message` | `string` | yes | Human-readable description for operator diagnostics |

### Outcome Classification

| HTTP status | `status` field | `issue` present | Gavel tier |
|------------|----------------|-----------------|------------|
| 2xx | `"ok"` | no | `PROCESS_SUCCESS` |
| 2xx | `"ok"` | yes | `PROCESS_SUCCESS_WITH_ISSUE` |
| 2xx | `"error"` | any | `PROCESS_FAILURE` |
| non-2xx | — (body may be absent) | — | `PROCESS_FAILURE` |
| Script: exit 0 | `"ok"` | no | `PROCESS_SUCCESS` |
| Script: exit 0 | `"ok"` | yes | `PROCESS_SUCCESS_WITH_ISSUE` |
| Script: exit 0 | `"error"` | any | `PROCESS_FAILURE` |
| Script: exit ≠ 0 | — (not read) | — | `PROCESS_FAILURE` |

### Example — Success

```json
{
  "status": "ok",
  "result": {
    "output": "I'm doing well, thank you for asking!"
  },
  "metadata": {
    "timing_ms": 342,
    "model": "llama3"
  },
  "issue": null,
  "trace_id": "run-20240601-abc123"
}
```

### Example — Success With Warning

```json
{
  "status": "ok",
  "result": {
    "output": "I'm doing well."
  },
  "metadata": {},
  "issue": {
    "code": "low_confidence",
    "level": "warning",
    "message": "Model confidence below threshold (0.42)"
  },
  "trace_id": "run-20240601-abc123"
}
```

### Transport Notes

- **HTTP:** Response body must be `Content-Type: application/json`. Non-2xx responses are
  classified as `PROCESS_FAILURE` before parsing the envelope.
- **Script:** Read from `{tmpdir}/response.json` after process exits with code 0. A
  non-zero exit skips envelope parsing and is classified directly as `PROCESS_FAILURE`.
  The response filename is configurable via `TestSubject.config.response_filename`
  (default `response.json`). Path traversal (`../`) in the filename is rejected.

---

## 3. Judge Request (HTTP + Script)

**Used by:** HTTP transport (POST body to the judge endpoint) and script transport (written
as `request.json` in the judge subprocess temp directory).

**Pydantic model:** `gavel_ai.models.runtime.ExternalJudgeRequest`

### Properties

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scenario_id` | `string` | yes | Scenario identifier from `scenarios.json` |
| `processor_output` | `string` | yes | The SUT's raw output to be scored (max 32 KB — see Truncation Limits) |
| `criteria` | `string` | yes | Rendered judge criteria / scoring rubric |
| `expected_behavior` | `string \| null` | no (default `null`) | Expected behavior from the scenario (optional reference for the judge) |
| `custom_config` | `object` | no (default `{}`) | Pass-through of `JudgeConfig.config` for judge-specific settings |
| `trace_id` | `string \| null` | no (default `null`) | Run-level trace identifier for correlation with `telemetry.jsonl` |
| `metadata` | `object` | no (default `{}`) | Additional per-invocation metadata |

### Example

```json
{
  "scenario_id": "greet-en-001",
  "processor_output": "I'm doing well, thank you for asking!",
  "criteria": "Score 1-10. Award 10 for a warm, grammatically correct greeting response.",
  "expected_behavior": "A friendly, natural greeting response in English",
  "custom_config": {
    "model": "gpt-4o",
    "temperature": 0.0
  },
  "trace_id": "run-20240601-abc123",
  "metadata": {}
}
```

### Transport Notes

Same transport mechanics as the task request: HTTP sends as POST body with `X-Gavel-Trace-Id`
header; script writes to `{tmpdir}/request.json`.

---

## 4. Judge Response (HTTP + Script)

**Used by:** HTTP transport (JSON response body from the judge) and script transport (read
as `response.json` from the judge subprocess temp directory).

**Pydantic model:** `gavel_ai.models.runtime.ExternalResponseEnvelope`

Same envelope model as the task response. The `result` object should contain judge-specific
fields (`score`, `reasoning`, optionally `evidence`):

### Expected `result` Fields for Judge Responses

| Field | Type | Description |
|-------|------|-------------|
| `result.score` | `number` | Score on a 1–10 scale |
| `result.reasoning` | `string` | Judge's explanation of the score |
| `result.evidence` | `string` | (Optional) supporting evidence |

### Example — Judge Success

```json
{
  "status": "ok",
  "result": {
    "score": 9,
    "reasoning": "The response is warm, grammatically correct, and appropriately brief."
  },
  "metadata": {
    "timing_ms": 512
  },
  "issue": null,
  "trace_id": "run-20240601-abc123"
}
```

### Transport Notes

Same as task response transport notes.

---

## Cross-References

- **Configuration:** How to configure `test_subject_type: "external"` with `protocol: "http"`
  or `protocol: "script"` → [schema-configs.md](schema-configs.md)
- **Outputs:** How `metadata["trace_id"]` appears on `OutputRecord`/`JudgedRecord` entries
  and links to `telemetry.jsonl` → [schema-outputs.md](schema-outputs.md)
- **Generated schemas:** `docs/specs/schemas/` (JSON Schema Draft 2020-12)
