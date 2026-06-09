
---
summary: "Lets Gavel delegate task and judge execution to systems outside its own process via test_subject_type: 'external' with protocol 'http' or 'script' — completing the existing stubbed closed-box HTTP path, and adding a script path that hands off via OS temp-dir request/response documents (auto-cleaned on completion). Both transports propagate Gavel's run trace_id, carry fully-specified request payloads (scenario data, task/judge custom config, required prompts/judge content) and structured response payloads (results, timing/turns/custom metadata, error/warning info), and distinguish 'process failure' (4xx/5xx or pre-completion abort, gated by abort_on_exec_failure, default true) from 'process success with internal error/warning' (gated by abort_on_process_error, default false). Documented schemas define both HTTP and file handoffs for tasks and judges. Reuses the existing ClosedBoxInputProcessor/RemoteSystemInput contracts and Step/Processor pipeline. Also reserves a forward-compatible `adapter` field (default 'gavel', additive) and a transport/wire-format seam for a future front-door (native-protocol) testing initiative — no MVP scope change."
phase: "clarify"
when_to_load:
  - "When defining or reviewing initiative goals, users, scope, success criteria, and risks."
  - "When validating that implementation still aligns with the intended problem and outcomes."
depends_on: []
modules:
  - "src/gavel_ai/core/steps/scenario_processor.py"
  - "src/gavel_ai/core/steps/judge_runner.py"
  - "src/gavel_ai/processors/closedbox_processor.py -> external_http_processor.py (renamed, ADR-8)"
  - "src/gavel_ai/skill/gavel-skill/ (SKILL.md, references/config-schema.md — correction, ADR-9)"
  - "src/gavel_ai/processors/ (new script processor + scaffold base classes)"
  - "src/gavel_ai/models/config.py (TestSubject, EvalConfig)"
  - "src/gavel_ai/models/runtime.py (OutputRecord, ProcessorResult)"
  - "src/gavel_ai/telemetry/ (spans.py, metadata.py)"
index:
  executive_summary: "## Executive Summary"
  project_classification: "## Project Classification"
  success_criteria: "## Success Criteria"
  user_journeys: "## User Journeys"
  scope: "## Scope"
  functional_requirements: "## Functional Requirements"
  non_functional_requirements: "## Non-Functional Requirements"
  open_questions: "## Open Questions"
  risk_mitigation: "## Risk Mitigation"
next_section: "Executive Summary"
---

# PRD: external-runner

## Progress

- [x] Executive Summary
- [x] Project Classification
- [x] Success Criteria
- [x] User Journeys
- [x] Scope & Phasing
- [x] Functional Requirements
- [x] Non-Functional Requirements
- [x] Open Questions
- [x] Risk Mitigation

## Executive Summary

**external-runner** lets Gavel delegate task execution and judge execution to systems that live outside Gavel's own process — reached either through a network API call (`protocol: "http"`) or by launching a local script/process (`protocol: "script"`) — while keeping every run's results, telemetry, trace correlation, and error semantics intact. It is for Builders who already have task-runner or judge infrastructure (internal services, CI pipelines, language-specific tooling, sandboxed environments) and want Gavel to orchestrate evals against that infrastructure rather than re-implementing it inside Gavel's process. It also gives the people *building* those external systems-under-test a head start: scaffolded base classes that handle input validation, telemetry/log propagation, and response formatting on the system-under-test side of the contract.

### What Makes This Special

- **Completes an existing half-built path** — `ClosedBoxInputProcessor` and `RemoteSystemInput` already implement HTTP-based remote execution; the wiring in `ScenarioProcessorStep` that converts scenarios into remote inputs is stubbed out. This initiative finishes that path (renaming `test_subject_type` from `"in-situ"` to `"external"`) rather than building a parallel one.
- **Two-sided contract, not just an orchestration change** — alongside the Gavel-side processors, the initiative ships scaffold base classes (`ScriptSystemUnderTest` / `RemoteSystemUnderTest`-style) that anyone implementing an external task or judge can inherit from, getting input parsing/validation, log/span emission, and schema-conformant response construction for free — turning the documented schemas (FR-6) from "read the docs and hope" into "subclass and fill in one method."
- **One mechanism, two transports, documented contracts** — both the HTTP and script transports funnel through the same `ProcessorResult` / `OutputRecord` contracts and share clearly defined, documented request/response schemas, so judges, reporting, and reflection work unchanged regardless of where execution happened.
- **Two-tier failure model** — the system distinguishes a *process failure* (the external task/judge didn't run to completion — surfaced as 4xx/5xx over HTTP or an abort signal over script, gated by `abort_on_exec_failure`, default `true`) from a *process success carrying an internal error/warning* (the external system ran fine but flagged a problem with its own output, gated by `abort_on_process_error`, default `false`) — so Builders can tune halting behavior independently for each.
- **Trace continuity across the boundary** — Gavel's run `trace_id` is propagated to the external system (HTTP header or request-document field) and threaded back through `OutputRecord`/`JudgedRecord`, so external executions remain correlatable in `telemetry.jsonl` instead of becoming an observability dead zone.

## Project Classification

**Technical Type:** Developer Tool / Evaluation Framework Extension
**Domain:** Infrastructure / LLM Evaluation Orchestration
**Complexity:** Medium — two new/completed execution transports plus a trace-propagation contract change, but built on existing pipeline abstractions (`Step`, `Processor`, `OutputRecord`) rather than new architecture.
**Project Context:** Brownfield — extends `ScenarioProcessorStep`, `JudgeRunnerStep`, and `ClosedBoxInputProcessor`, which already exist in partial/stubbed form.

---

## Success Criteria

### User Success

A user achieves success when they can:

1. **Point a scenario at an external HTTP endpoint and get real results** — configuring `test_subject_type: "external"` with `protocol: "http"` produces populated `results_raw.jsonl` records sourced from the remote endpoint, where today the path silently produces nothing.
2. **Point a scenario at a local script and get real results** — configuring `protocol: "script"` launches the configured script/binary, exchanges a request/response document pair through an auto-cleaned OS temp directory, and produces populated `OutputRecord`s identical in shape to in-process results.
3. **Trace an external execution end-to-end** — given a `run_id`, the user can find the corresponding external call/process invocation in `telemetry.jsonl` via a shared `trace_id`, without manual timestamp correlation.
4. **Run judges externally using the same mechanisms** — a judge configured to call out to an external scorer (API or script) produces `JudgedRecord`s through the existing `results_judged.jsonl` pipeline, indistinguishable in structure from in-process judge output.
5. **Distinguish "it didn't run" from "it ran but flagged a problem"** — when an external task/judge fails to execute (errors before completion, e.g. its own input validation), Gavel treats it as a process failure (4xx/5xx over HTTP, an abort signal over script); when it completes but reports an internal problem (e.g. its LLM output failed validation), Gavel treats it as a process success carrying an error/warning code. `abort_on_exec_failure` (default `true`) and `abort_on_process_error` (default `false`) let the Builder tune halting behavior for each independently.
6. **Build an external system without re-deriving the contract** — a developer building a system-under-test subclasses a scaffold base class (`ScriptSystemUnderTest` / `RemoteSystemUnderTest`), implements one method, and gets input validation, telemetry/log emission, and schema-conformant response assembly for free — and can find a ready-to-edit copy of that scaffold in the eval's `scripts/` directory if they're starting fresh.

### Technical Success

The system is successful when:

1. **`ScenarioProcessorStep` builds real `RemoteSystemInput`/script-invocation objects** for `external` test subjects instead of passing an empty input list to `ExternalHttpProcessor` (renamed from `ClosedBoxInputProcessor`, see ADR-8).
2. **A new script processor exists alongside `ExternalHttpProcessor`**, sharing the `Processor` interface, using an OS temp directory (auto-cleaned on completion) for request/response document handoff, and returning `ProcessorResult` so downstream code is untouched.
3. **`trace_id` flows out and back**: present in the outbound HTTP header / request document, and present on the inbound `OutputRecord`/`JudgedRecord` (or resolvable via `metadata`) so it lands in telemetry correlation without a schema break for in-process records.
4. **Judge execution can be delegated** through the same two transports via a documented config shape, reusing `JudgeExecutor`'s batching/result contracts.
5. **Request payloads are complete and response payloads are structured**: every external invocation receives all relevant scenario info, the task/judge's custom config from `eval_config`, and required prompt/judge content; every response is parsed into scenario results, timing/turns/custom metadata, and error/warning info per the documented schema.
6. **Process-failure and process-error are classified distinctly**: exec failures (non-2xx/abort, pre-completion errors) raise through `abort_on_exec_failure`; in-band error/warning codes on otherwise-successful responses raise through `abort_on_process_error` — both routed through the existing `IssueClassifier`/`ErrorPolicy` machinery.
7. **Scaffold base classes exist and are usable**: `ScriptSystemUnderTest` and `RemoteSystemUnderTest` (or equivalents) are importable from Gavel, handle validation/telemetry/response-assembly internally, and require subclasses to implement only the core "do the work" method.

### Measurable Outcomes

- An eval config with `test_subject_type: "external"` / `protocol: "http"` produces non-empty `results_raw.jsonl` (currently produces zero records due to the stub).
- A new `protocol: "script"` eval config produces `results_raw.jsonl` records with `timing_ms`, `tokens_*` (where available), and `error`/`warning` fields populated to the same schema as in-process records, with no leftover temp files after the run.
- 100% of external-execution `OutputRecord`/`JudgedRecord` entries carry a `trace_id` resolvable to a span in `telemetry.jsonl` for the same `run_id`.
- A documented JSON Schema (or equivalent) exists for each of: HTTP task request, HTTP task response, HTTP judge request, HTTP judge response, script task request document, script task response document, script judge request document, script judge response document.
- A minimal subclass of each scaffold base class (overriding only the "do the work" method) round-trips a real Gavel-generated request into a schema-valid response, with logs/spans correlated to the inbound `trace_id` — demonstrated for both script and HTTP transports.

---

## User Journeys

### Journey 1: Platform Engineer — "We already have a task runner, let Gavel drive it"

A platform engineer's team runs candidate responses through an internal HTTP service that wraps several proprietary models behind a stable API. Today they can configure `test_subject_type: "in-situ"` and point at that service, but the run silently produces no output records — the engineer has to dig into `scenario_processor.py` to discover the path is unfinished. With external-runner, they configure `test_subject_type: "external"` / `protocol: "http"`; Gavel sends a fully-specified request (scenario data, the test subject's custom config, required prompts, `trace_id` header) and gets back real `OutputRecord`s with latency, token counts (where reported), and any error/warning the service flagged — and the call is traceable back to the Gavel run that triggered it. If the endpoint 5xxs, that's a clean process failure; if it 200s but reports "output failed our internal validator," that's a process success carrying an internal error code, and the engineer can choose (via `abort_on_process_error`) whether that should halt the run.

**Requirements Revealed:** Complete the `external`/HTTP wiring end-to-end (scenario → `RemoteSystemInput` → `ExternalHttpProcessor` → `OutputRecord`); documented HTTP request/response schemas; propagate `trace_id` via HTTP header; two-tier error classification (`abort_on_exec_failure` / `abort_on_process_error`).

### Journey 2: ML Engineer — "Our scorer only runs in a sandboxed local environment"

An ML engineer has a judge that must run in an isolated local environment (different language runtime, restricted network access) that can't be hosted inside Gavel's process. They configure `protocol: "script"`: Gavel creates an OS temp directory for the invocation, writes a request document containing the rendered prompt/judge content, scenario fields, the judge's custom config, and `trace_id`; launches the script; the script writes a response document with its score, reasoning, timing/turn metadata, and any error/warning code; Gavel reads it back, produces a `JudgedRecord` exactly as if an in-process LLM judge had run, and the temp directory is cleaned up automatically when the invocation completes — win or lose. A script that crashes before writing a response is a process failure (`abort_on_exec_failure`); a script that completes but reports "low confidence in this score" is a process success with a warning code (`abort_on_process_error`).

**Requirements Revealed:** Symmetric request/response document convention in an auto-cleaned OS temp dir; documented script request/response schemas for both tasks and judges; subprocess lifecycle management (timeout, exit code, stderr capture) via existing `async_config`/error-policy patterns; two-tier error classification; reuse of `JudgeExecutor` result contracts.

### Journey 3: Systems-Under-Test Developer — "I'm building the thing Gavel is going to call"

A developer on a different team is asked to make their service or script callable by Gavel as an external task or judge. Rather than reverse-engineering the documented schemas (FR-6) by hand, they import a scaffold base class — `RemoteSystemUnderTest` for an HTTP service, `ScriptSystemUnderTest` for a script — subclass it, and implement just the "do the work" method. The base class already parses and validates the incoming request against the documented schema, exposes the scenario data/custom config/prompt content/`trace_id` as typed attributes, emits logs and telemetry spans correlated to the inbound `trace_id`, and assembles a syntactically valid response (including the `status`/`issue` envelope from FR-5/FR-6) from whatever the subclass returns. If they're starting a brand-new eval, the scaffold even shows up pre-populated in the eval's `scripts/` directory as a starting point to edit directly.

**Requirements Revealed:** Two scaffold base classes (local-script and remote/HTTP) shipped inside Gavel for direct import; built-in request parsing/validation against the documented schemas; built-in log/telemetry-span emission correlated to the inbound `trace_id`; built-in assembly of schema-conformant responses (including the two-tier `status`/`issue` envelope); optional materialization of the scaffold into an eval's `scripts/` directory at eval-creation time.

### Journey Requirements Summary

| User Type | Key Requirements |
|-----------|-----------------|
| **Platform Engineer (HTTP)** | Working `external`/`http` path, documented request/response schemas, trace_id in request headers, two-tier error classification |
| **ML Engineer (script)** | `script` protocol, temp-dir request/response document exchange with auto-cleanup, documented script schemas (task + judge), trace_id in request document, subprocess lifecycle + two-tier error classification, judge delegation |
| **Systems-Under-Test Developer** | Importable scaffold base classes (script + remote), built-in input validation/typed access, log/span emission correlated to `trace_id`, schema-conformant response assembly, optional scaffold-into-`scripts/` materialization at eval creation |

---

## Scope

### MVP — Minimum Viable Product (v1)

**Core Deliverables:**
- Rename `test_subject_type: "in-situ"` → `"external"`, with `protocol: "http" | "script"` selecting the transport (config/schema/docs migration included).
- Rename `ClosedBoxInputProcessor`/`closedbox_processor.py` → `ExternalHttpProcessor`/`external_http_processor.py` (and its test module) so the code's name matches the `"external"` vocabulary it now serves, rather than leaving a permanent code/concept mismatch (see tech-design ADR-8).
- Complete the HTTP path: `ScenarioProcessorStep` converts scenarios into `RemoteSystemInput` and routes them through `ExternalHttpProcessor` (renamed from `ClosedBoxInputProcessor`) to populated `OutputRecord`s.
- Correct the packaged `gavel-skill`'s stale reference docs (`references/config-schema.md`, and the relevant `SKILL.md` setup/debug flows) so they describe the real `"local"`/`"external"` + free-text `protocol` model instead of the outdated `"local"`/`"remote"` + enum `protocol` shape — a blocking precondition, since the skill is the primary Builder-facing surface for configuring and debugging any non-`local` eval (see tech-design ADR-9).
- New script execution path: a processor that, per invocation, creates an OS temp directory (auto-cleaned on completion regardless of outcome), writes a request document, launches the configured script/process, waits for a response document, and parses it into `ProcessorResult`/`OutputRecord`.
- Fully-specified request payloads for both transports: relevant scenario info for that invocation, the task/judge's custom config from `eval_config`, and all required prompt/judge content.
- Structured response payloads for both transports: scenario results, metadata (timing, turns, custom fields), and error/warning info.
- Two-tier error classification with configurable abort flags: `abort_on_exec_failure` (default `true`, for process/exec failures — non-2xx/5xx HTTP or pre-completion script aborts) and `abort_on_process_error` (default `false`, for in-band error/warning codes on otherwise-successful responses), wired through `IssueClassifier`/`ErrorPolicy`.
- `trace_id` propagation: outbound via HTTP header (HTTP path) and request-document field (script path); inbound correlation onto `OutputRecord`/`JudgedRecord` (field or documented `metadata` key).
- External judge execution reusing both transports, producing `JudgedRecord`s through the existing judge pipeline.
- **Documented schemas** (e.g. JSON Schema) for HTTP and script request/response payloads, separately for tasks and for judges — published in `docs/specs/` alongside the existing config/output schema references.
- **Scaffold base classes** — `ScriptSystemUnderTest` and `RemoteSystemUnderTest` (or equivalents) shipped inside Gavel for direct import, handling input validation against the documented schemas, log/telemetry-span emission correlated to `trace_id`, and schema-conformant response assembly; plus a mechanism to materialize a starter copy into an eval's `scripts/` directory at eval-creation time.

**Quality Gates:**
- An eval run against a real (or test-double) HTTP endpoint produces correct, non-empty `results_raw.jsonl`, with request/response payloads conforming to the documented schemas.
- An eval run against a script produces correct `results_raw.jsonl` with the same record schema as in-process runs, including populated `error`/`warning` fields, and leaves no temp files behind on success or failure.
- A process failure (exec error, malformed/missing response, non-2xx/timeout) is classified distinctly from a process success carrying an internal error/warning code, and each respects its own abort flag.
- A `trace_id` present on an external-execution `OutputRecord` resolves to a span for the same `run_id` in `telemetry.jsonl`.
- Existing in-process (`local`) test-subject runs are unaffected (no regressions in `ScenarioProcessorStep`/`JudgeRunnerStep` for the existing path).
- A minimal subclass of each scaffold base class successfully round-trips a real Gavel request into a valid response (script and HTTP), and a freshly-created eval that opts into external execution finds a scaffold file already present in its `scripts/` directory.

### Growth Features (Post-MVP)

**v2: Additional transports & polling**
- Stdout-capture variant of the script mechanism (for tools that print results rather than writing files), as a configurable alternative to file-drop.
- Long-running/async external jobs: poll-for-completion pattern for HTTP systems that return a job ID rather than a synchronous result.

**v3: Richer protocol support**
- **Front-door testing via native wire-format adapters** — calling a service through the wire protocol it already speaks to real users (e.g. OpenAI chat-completions JSON), with no Gavel-specific glue required on the service side, as a concrete and explicit next step beyond this initiative's "side door" (Gavel's own bespoke envelope). Enabled by an `adapter` field (e.g. `adapter: "openai_chat"` alongside `protocol: "http"`) — orthogonal to `protocol` (transport: how bytes move) and naming the wire format (what shape the payload is) — that this initiative reserves now (default `"gavel"`, additive, no MVP behavior change; see tech-design ADR-10).

### Vision (Future)

- A pluggable external-runner registry so Builders can register custom transports (gRPC, message queues, cloud functions) without modifying core pipeline code.

---

## Functional Requirements

### 1. Configuration & Naming

**FR-1.1:** Rename the `test_subject_type` value `"in-situ"` to `"external"` across `EvalConfig`/`TestSubject` models, code, schema docs, and any sample configs; `protocol` becomes a required field on external test subjects with allowed values `"http"` and `"script"`.
- Decide and document migration behavior for existing configs that use `"in-situ"` (hard rename vs. accepted alias) — see Open Questions.

**FR-1.2:** Extend `TestSubject.config` (or equivalent) with the fields needed per protocol: for `"http"` — endpoint, method, headers, auth, trace-header name; for `"script"` — command/args, working directory, timeout override, request/response document field names.

**FR-1.3:** Add `abort_on_exec_failure: bool = True` and `abort_on_process_error: bool = False` as configurable flags on the external test subject (and on external judge configs — see FR-7), with these defaults applying when unset.

---

### 2. HTTP / Network-API Execution (completing the external/http path)

**FR-2.1:** `ScenarioProcessorStep` must convert each scenario destined for an `external`/`http` test subject into a `RemoteSystemInput` (endpoint, method, headers, body, auth) populated from the test subject's `system_id`, `protocol`, and `config`, and pass the resulting list to `ExternalHttpProcessor` (renamed from `ClosedBoxInputProcessor`, ADR-8).
- Currently `inputs` is always empty for this path (`scenario_processor.py` ~line 306); this must produce one `RemoteSystemInput` per scenario/variant combination consistent with how `PromptInput` is built for local evals.

**FR-2.2:** The outbound HTTP request body must be a fully-specified **task request payload** per the documented HTTP task-request schema (see FR-6), containing: all relevant scenario info for that invocation, the test subject's custom config (from `eval_config`), and the rendered prompt(s)/required prompt content. The request must also carry the run's `trace_id` (configurable header, with a documented default name).

**FR-2.3:** The inbound HTTP response must be parsed per the documented HTTP task-response schema (see FR-6) into a `ProcessorResult`/`OutputRecord` carrying: scenario result content, metadata (timing, turns, custom fields as reported), and any error/warning info — converted to the same required `OutputRecord` fields (`timing_ms`, `error`, `metadata`, `timestamp`, `trace_id`-resolvable) as in-process results.

**FR-2.4:** HTTP responses must be classified into the two-tier error model (see FR-5): a non-2xx (typically 4xx/5xx), unreachable endpoint, or malformed body is a **process failure**; a 2xx response whose payload itself carries an internal error/warning code is a **process success with internal error/warning**.

---

### 3. Script Execution

**FR-3.1:** A new processor (e.g. `ScriptInputProcessor`) must launch a configured script or executable as a subprocess for each scenario/variant combination, conforming to the existing `Processor` interface so it slots into `ScenarioProcessorStep` alongside `PromptInputProcessor` and `ExternalHttpProcessor`.

**FR-3.2:** Each invocation must use a dedicated **OS temp directory** (e.g. `tempfile.TemporaryDirectory`) created immediately before launch and removed automatically when the invocation completes — success or failure — so no handoff artifacts persist on disk, and concurrent invocations (`async_config.num_workers > 1`) never collide.

**FR-3.3:** Before launching, Gavel must write a **request document** (JSON) into that temp directory per the documented script task-request schema (see FR-6), containing: all relevant scenario info for that invocation, the test subject's custom config, the rendered prompt(s)/required content, and the run's `trace_id`.

**FR-3.4:** After the process exits (or signals completion), Gavel must read a **response document** (JSON) from the temp directory per the documented script task-response schema (see FR-6) and parse it into a `ProcessorResult` containing: scenario result content, metadata (timing, turns, custom fields), and error/warning info.

**FR-3.5:** Subprocess invocation must use argument-list form (no `shell=True` with interpolated strings) and must integrate with existing async/error-policy machinery: respect `async_config.task_timeout_seconds` (terminate on timeout), capture exit codes and stderr, and classify failures per the two-tier model (see FR-5).

---

### 4. Trace Correlation

**FR-4.1:** The current run's `trace_id` (from `telemetry/spans.py`'s run-level trace configuration) must be made available to both processors at construction/invocation time.

**FR-4.2:** `OutputRecord` and `JudgedRecord` produced via either external-execution transport must carry the `trace_id` in a resolvable, documented location, enabling a user to join `results_raw.jsonl`/`results_judged.jsonl` rows to `telemetry.jsonl` spans without timestamp-based heuristics.

**FR-4.3:** `docs/specs/schema-outputs.md` must document how `trace_id` appears on externally-executed records (vs. its absence on in-process records, where correlation remains via `run_id`).

---

### 5. Two-Tier Error Classification

**FR-5.1: Process failure** — the external task/judge did not run to completion (HTTP: non-2xx, typically 4xx/5xx, unreachable, timeout, malformed body; script: non-zero exit, crash, missing/unparseable response document, timeout, pre-completion validation error). Gated by `abort_on_exec_failure` (default `true`): when `true`, classify as `ERROR` (halts per `ErrorPolicy`); when `false`, classify as `WARNING`/recoverable per `IssueClassifier` semantics.

**FR-5.2: Process success with internal error/warning** — the external task/judge completed and returned a well-formed response, but the response itself carries an error or warning code (e.g. "LLM output failed our validation"). Gated by `abort_on_process_error` (default `false`): when `true`, classify as halting; when `false`, record the error/warning on the `OutputRecord`/`JudgedRecord` and continue.

**FR-5.3:** Both tiers must route through the existing `IssueClassifier`/`ErrorPolicy` machinery (`classify`/`classify_message`, `Step.safe_execute`, `error_policy.should_halt`) rather than introducing parallel halting logic.

---

### 6. Documented Schemas (Tasks & Judges, HTTP & Script)

**FR-6.1:** Publish a documented schema (e.g. JSON Schema, alongside `docs/specs/schema-configs.md`/`schema-outputs.md`) for each of the eight request/response payload shapes: HTTP task request/response, HTTP judge request/response, script task request/response document, script judge request/response document.

**FR-6.2:** Each request schema must specify, at minimum: scenario fields relevant to that invocation, the task/judge's custom config (from `eval_config`), required prompt or judge-criteria content, and `trace_id`.

**FR-6.3:** Each response schema must specify, at minimum: scenario result content (task output, or judge score/reasoning/evidence), metadata (timing, turn count where applicable, custom fields), and a structured error/warning section that distinguishes the two tiers from FR-5 (e.g. a `status: "ok" | "error"` envelope plus an optional `issue: {code, level, message}`).

---

### 7. External Judge Execution

**FR-7.1:** Judges may be configured to delegate scoring to an external system via the same two transports (`http` / `script`), using a config shape consistent with `TestSubject`'s `protocol`/`config`/`system_id` pattern (and the same `abort_on_exec_failure`/`abort_on_process_error` flags) so Builders learn one mechanism for both task and judge delegation.

**FR-7.2:** External judge invocations must produce results that flow through the existing `JudgeExecutor`/storage path into `JudgedRecord`s (`judge_id`, `score`, `reasoning`, `error`, `timestamp`), indistinguishable in shape from in-process LLM-judge output, and conforming to the documented judge request/response schemas (FR-6).

**FR-7.3:** External judge invocations must propagate and surface `trace_id` per FR-4, identical to task-execution delegation.

---

### 8. Scaffold Base Classes for Systems Under Test

**FR-8.1:** Ship two importable base classes inside Gavel — one for script-based systems under test (e.g. `ScriptSystemUnderTest`) and one for HTTP/remote systems under test (e.g. `RemoteSystemUnderTest`) — that anyone implementing an external task or judge can subclass directly, for both task-execution and judge roles.

**FR-8.2:** Each base class must, on the systems-under-test side of the contract:
- **Read & validate inputs** — parse the inbound request (document for script, request body for HTTP) against the documented schemas (FR-6) and expose scenario data, custom config, prompt/judge content, and `trace_id` as typed attributes; reject malformed input with a clear, schema-referencing error.
- **Emit logs and telemetry spans** — produce structured logs and OTEL-compatible spans correlated to the inbound `trace_id`, using a pattern consistent with Gavel's own `telemetry/spans.py` conventions, so the system-under-test's own execution is traceable alongside Gavel's run.
- **Return syntactically valid responses** — assemble the outbound response (document for script, response body for HTTP) per the documented response schemas (FR-6), including the `status`/`issue` envelope distinguishing the two error tiers (FR-5), from a minimal subclass-provided result.

**FR-8.3:** The base classes must require subclasses to implement only the "do the work" surface (e.g. a single `handle(request) -> result` style method) — all schema parsing/validation, telemetry, and response assembly are handled by the base class.

**FR-8.4:** Provide a mechanism to materialize a copy of the relevant scaffold(s) into an eval's `scripts/` directory at eval-creation time (e.g. via `gavel init` or an eval-scaffolding command), so a Builder starting a new external-task/judge eval gets a ready-to-edit starting file rather than having to locate and import the base class manually.
- The in-Gavel base classes remain the source of truth; materialized copies are a convenience starting point, not a fork — document this distinction clearly so Builders understand which to update when Gavel's contract changes.

---

## Non-Functional Requirements

- **Performance:** External execution (HTTP or script) must respect `async_config.num_workers`/concurrency settings already governing in-process execution; no global serialization introduced by the new processors; per-invocation temp-directory creation must not become a concurrency bottleneck.
- **Reliability:** Failures in external systems (HTTP errors, malformed responses, script crashes, timeouts, missing response documents) must be classified via `IssueClassifier` into the two-tier model (FR-5) and handled via `ErrorPolicy`/the new abort flags — no silent data loss (the current stub silently produces nothing, which this initiative explicitly fixes). Temp directories must be cleaned up even when the invocation errors or times out.
- **Security:** Script execution must not introduce shell-injection risk — commands/arguments must be invoked via argument lists (no `shell=True` with interpolated strings), and request/response document paths must be confined to the per-invocation OS temp directory (no Builder-supplied path traversal).
- **Maintainability:** New processors must conform to the existing `Processor`/`ProcessorResult` interface so `ScenarioProcessorStep`, `JudgeRunnerStep`, reporting, and reflection require no structural changes — only routing/construction logic changes. The eight documented payload schemas (FR-6) become the contract surface for both Gavel-side parsing and external-system implementers.

---

## Open Questions

- **Where does `trace_id` live on `OutputRecord`/`JudgedRecord`?** A first-class field (schema change affecting all records) vs. a documented `metadata["trace_id"]` key (no schema break, but less discoverable). This needs a tech-design decision before FR-4.x can be finalized.
- **Migration for existing `"in-situ"` configs**: does renaming to `"external"` (FR-1.1) require a hard cutover, a deprecation alias with a warning, or a config-migration script? Affects how broadly `EvalConfig` schema/docs/sample-config changes ripple.
- **Timeout semantics for scripts that exceed `task_timeout_seconds`**: terminate (SIGTERM then SIGKILL?) and classify as a process failure — confirm this is the intended behavior and whether it should be configurable independently of the global async timeout.
- **Schema format and location for the eight documented payloads (FR-6)**: JSON Schema files under `docs/specs/`? Pydantic models exported as schema? Co-located with `schema-configs.md`/`schema-outputs.md` or a new `schema-external-runner.md`?
- ~~**Custom config resolution for judges (FR-7.1/FR-6.2)**: judges already support `config_ref`/`markdown_path`/`criteria` — does "the judge's custom config" in the external request payload mean the resolved/rendered judge content, the raw config block, or both?~~ **Resolved**: rendered/resolved judge content only (not the raw `config_ref`/`markdown_path`/`criteria` config block) — encoded in `approach.md` Partition 4 ("constructing `RemoteSystemInput`/`ScriptSystemInput` from judge-specific request content — rendered judge criteria/prompt instead of task prompts") and `tasks.md` id 41.
- **Where do the scaffold base classes live, and how do they get into `scripts/` (FR-8.4)?** Options include: a packaged module under `gavel_ai` that `gavel init`/eval-creation copies verbatim into `scripts/`, a templating mechanism similar to reporter templates (`reporters/templates/*`), or a CLI subcommand (`gavel scaffold ...`) invoked on demand. Needs a tech-design decision, including how materialized copies stay distinguishable from the canonical in-Gavel versions as the contract evolves.
- **What telemetry/span emission contract do the scaffold base classes follow?** Should they emit raw OTEL spans compatible with any collector, mirror Gavel's own `TelemetryFileExporter`/JSONL convention so logs land alongside `telemetry.jsonl`, or both — and how is the collector endpoint/sink configured for an external process that may run in a different environment than Gavel?

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Completing the stubbed external/http path surfaces deeper architectural gaps (e.g. variant/model semantics don't map cleanly to "calling an external system") | Medium | Medium | Timebox an investigation spike during tech-design; if gaps are large, scope MVP to the cleanest subset and document follow-ups rather than redesigning broadly |
| Script execution introduces security exposure (shell injection, path traversal via configured script paths) | Low | High | Enforce argument-list subprocess invocation, confine all document I/O to the per-invocation OS temp directory, document the trust assumption that configured scripts are Builder-authored |
| Renaming `test_subject_type: "in-situ"` → `"external"` breaks existing configs/docs/tests referencing the old value | Medium | Medium | Grep-audit all references before renaming; decide migration approach explicitly (Open Questions) rather than leaving a silent break |
| Renaming `ClosedBoxInputProcessor`/`closedbox_processor.py` → `ExternalHttpProcessor`/`external_http_processor.py` misses a reference (import, docstring, test module) and silently breaks the HTTP path or its test suite | Low | Medium | Grep-audit all `closedbox`/`ClosedBox` occurrences before renaming (bounded to ~14 files per tech-design ADR-8 "Affects"); bundle the rename into the same implementation slice as the HTTP-path completion work so one engineer owns both diffs and the test module rename together |
| The packaged `gavel-skill`'s reference docs are already stale for the *current* `"local"`/`"in-situ"` model (documenting a `"remote"`/enum-`protocol` shape that doesn't exist), so Builders asking the skill to configure or debug an `external` eval get actively wrong guidance — not just incomplete guidance | Medium | High | Treat the `references/config-schema.md` correction as a blocking MVP precondition (not a follow-on doc task), sequenced into the Foundation slice (tech-design ADR-9) so it lands before any Builder-facing `external` guidance is needed; extend `SKILL.md`'s setup/debug flows only once the underlying `external` path is functional and testable |
| Two-tier error classification (FR-5) is misclassified at the boundary (e.g. a malformed-but-200 response treated as success) | Medium | Medium | Define the `status`/`issue` envelope precisely in the documented schemas (FR-6) so classification is driven by explicit fields, not heuristics; cover both tiers in tests |
| Adding `trace_id` to output records breaks downstream consumers (reporters, judges, schema validators) expecting the current `OutputRecord` shape | Low | Medium | Prefer additive changes (`metadata` key or `Optional` field with safe default); validate against existing reporter templates and schema docs before merging |
| Materialized scaffold copies in an eval's `scripts/` directory drift from the canonical in-Gavel base classes as the contract evolves, leaving Builders on stale schemas | Medium | Medium | Treat materialized copies explicitly as starting points (not forks) in docs; consider a version marker/comment in the scaffold file pointing back to the canonical class so drift is detectable |
| This MVP only supports a "side door" (the tested service must implement Gavel's bespoke envelope) — Builders with services that already speak a native wire protocol (e.g. OpenAI chat-completions) get no direct path, and a future "front door" initiative could be forced into a costly refactor of shipped, tested processors if no seam exists | Medium | Low | Explicitly scope this initiative as side-door-only and reserve a clean, additive seam for front-door support now: an optional `adapter` field (default `"gavel"`, orthogonal to `protocol`) and a transport/wire-format/classification structuring convention in the shipped processors and `classify_external_outcome` (tech-design ADR-10) — so the next initiative adds a sibling adapter rather than refactoring shipped code |
