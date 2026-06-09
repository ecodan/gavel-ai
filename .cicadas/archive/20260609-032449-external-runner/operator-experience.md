
---
summary: "For Platform/ML Engineers, the primary interface to external-runner is the packaged `gavel-skill` Claude Code skill (the 'Gavel Eval Assistant') — they describe what they want ('point this eval at our HTTP service' / 'run our scorer script') and the skill walks them through `test_subject_type: external` / `protocol: http|script` config, abort-flag tuning, run execution, and debugging two-tier failures, reading from its `references/config-schema.md`/`cli-reference.md` (which this initiative must also bring up to date — they currently document a stale `local|remote` / `acp|open_ai` shape that doesn't match the real model). Systems-Under-Test Developers work more directly with documented schemas, structured output records, run logs/telemetry, and a scaffold starter file. The experience goal across both: make the two-tier failure model (process failure vs. process success-with-issue) immediately legible — whether surfaced by the skill conversationally or by raw logs/errors — keep config/output shapes consistent with existing Gavel conventions (Rich panel + run.log, no stack traces, additive trace_id), and let scaffold-based developers get a working system-under-test from one subclassed method."
phase: "ux"
when_to_load:
  - "When designing or reviewing config fields, run output, error/warning messages, logs, schema docs, or the scaffold starter experience for external-runner."
  - "When implementation questions depend on operator-facing behavior (messages, states, schema readability) rather than product UI."
depends_on:
  - "prd.md"
modules:
  - "src/gavel_ai/skill/gavel-skill/ (SKILL.md, references/config-schema.md, references/cli-reference.md — primary Builder-facing surface)"
  - "eval_config.json / TestSubject schema (test_subject_type, protocol, abort flags)"
  - "results_raw.jsonl / results_judged.jsonl (trace_id, error/warning, metadata)"
  - "run.log / Rich error panel (stderr)"
  - "telemetry.jsonl (external-invocation spans)"
  - "docs/specs/ (new payload schema docs)"
  - "eval scripts/ directory (scaffold starter files)"
index:
  operator_goals: "## Operator Goals and Constraints"
  surfaces: "## Affected Surfaces"
  flows: "## Operator Flows"
  states: "## States and Feedback"
  copy: "## Copy and Message Guidelines"
  accessibility: "## Accessibility and Readability"
next_section: "Operator Goals and Constraints"
---

# Operator Experience: external-runner

## Progress

- [x] Operator Goals and Constraints
- [x] Affected Surfaces
- [x] Operator Flows
- [x] States and Feedback
- [x] Copy and Message Guidelines
- [x] Accessibility and Readability

> **Why `operator-experience.md` instead of `ux.md`:** external-runner has zero screen-based UI — every interaction is through a conversational skill, config files, CLI runs, structured output records, logs, schema docs, and a code scaffold. All three PRD personas (Platform Engineer, ML Engineer, Systems-Under-Test Developer) are developers/operators, not end-users. This matches the `operator-experience.md` trigger conditions (CLI/config behavior, command output, logs, error/fallback messages, docs, **agent-facing workflow**) directly — and the last of those triggers is the dominant one here, because of the point below.

> **The skill is the primary CX for configuration and debugging.** Gavel ships `gavel-skill` (`src/gavel_ai/skill/gavel-skill/`) — a Claude Code Agent Skill billed as the "Gavel Eval Assistant," a "hands-on helper for every stage of working with the gavel-ai evaluation framework," covering setup, execution, and debugging. Most Platform/ML Engineers will reach `external` execution by *describing what they want to the skill*, not by hand-authoring `eval_config.json` from the schema docs. That makes the skill's `references/config-schema.md` and `references/cli-reference.md` — and the conversational flows in `SKILL.md` itself — the **primary operator-facing surface** for this initiative, with raw config/CLI/logs as the secondary (but still required, and still used directly by Systems-Under-Test Developers and anyone debugging deeply) surface. Flows 1 and 2 below are written skill-first for that reason.
>
> **This surface is currently stale and must be corrected as part of this initiative**, independent of anything else: `references/config-schema.md` documents `test_subject_type: "local" | "remote"` and `protocol: "acp" | "open_ai"` — neither of which matches the real `TestSubject`/`EvalConfig` model (`"local"` / `"in-situ"`→`"external"`, free-text `protocol`). Builders following the skill's *current* guidance today would configure something that doesn't validate. Bringing this doc in line with reality is not optional polish — it is the precondition for the skill to be able to walk anyone through `external` setup at all.

## Operator Goals and Constraints

**Primary goal:** A Builder should be able to ask the skill to "point this eval at our HTTP service" or "run our scorer as a script" and be walked, conversationally, to a correct `external` configuration — and when something goes wrong, the skill (or, failing that, the raw log/error output) should make immediately clear *which* of the two failure tiers occurred (process failure vs. process success-with-issue) and *where* to look (which invocation, which `trace_id`, which schema section). A Systems-Under-Test Developer should be able to go from "I was asked to make my service callable by Gavel" to "my service passes a round-trip test" by editing one method in a scaffold file.

**Constraints:**
- The skill's reference docs (`config-schema.md`, `cli-reference.md`) must accurately describe `external`/`http`|`script` config — including the abort flags and protocol-specific sub-shapes — *and* must be corrected for their existing `local|remote`/`acp|open_ai` staleness; an agent walking a Builder through setup is only as good as the references it reads (per `SKILL.md` §0: "Read the relevant reference files").
- Must follow existing Gavel CLI/config/output/log conventions exactly — no new paradigms introduced for this initiative alone (e.g., the existing "Rich panel to stderr + pointer to `run.log`, never a raw stack trace" convention applies unchanged to external-execution errors, and the skill should relay — not paraphrase away — that same framing when it surfaces an error).
- Error and warning messages (whether relayed by the skill or read raw) must be precise and stable enough that two independently-working engineers — one on the Gavel/config side, one on the external-system side — can build against the documented contract without needing to read each other's code.
- The `"in-situ"` → `"external"` rename must not silently break existing configs or silently mislead the skill; whatever migration path is chosen (Open Question in `prd.md`) must be visible and actionable to the operator — surfaced by the skill if the operator is working through it, and by config-validation messaging either way.
- Logging/telemetry for external invocations must integrate into the *existing* `telemetry.jsonl` / `run.log` / trace-correlation conventions — operators should never need to learn a second observability surface for external vs. in-process runs, regardless of whether they got there via the skill or directly.
- Noise control: per-invocation subprocess/HTTP-call logging must be informative without flooding `run.log` on large eval runs — follow the verbosity conventions already established for in-process LLM calls.

## Affected Surfaces

| Surface | Change | Compatibility Notes |
|---------|--------|---------------------|
| `gavel-skill` reference docs (`references/config-schema.md`, `references/cli-reference.md`) and `SKILL.md` setup/debug flows | **Corrected** to describe the real `test_subject_type`/`protocol` shape (replacing the stale `local\|remote` / `acp\|open_ai` documentation) and **extended** to walk a Builder through `external`/`http`\|`script` setup, abort-flag selection, and two-tier-failure debugging | This is a **fix-forward** change — the docs are wrong today regardless of this initiative; until corrected, the skill cannot correctly help with *any* non-`local` test subject, not just `external`. Treat as a blocking MVP item, not a nice-to-have |
| `eval_config.json` / `TestSubject` schema | New/renamed fields: `test_subject_type: "external"` (was `"in-situ"`), required `protocol: "http" \| "script"`, protocol-specific config (endpoint/headers/auth or command/args/timeout), `abort_on_exec_failure` / `abort_on_process_error` flags, and a new optional `adapter` field (default `"gavel"`, orthogonal to `protocol`, reserved for future native-protocol adapters — see `tech-design.md` ADR-10) | Old `"in-situ"` value handling depends on the migration decision in `prd.md` Open Questions — operator must see either an alias-with-deprecation-warning or a clear hard-cutover error naming the new value. `adapter` is invisible to operators who don't set it — omitting it leaves today's `external` experience completely unchanged |
| `results_raw.jsonl` / `results_judged.jsonl` | Populated records (where today the HTTP path produces none); new `trace_id` correlation; populated `error`/`warning`/`metadata` (timing, turns, custom) for externally-executed records | Purely additive — existing in-process record shape and content are unchanged |
| `run.log` / Rich error panel (stderr) | New human-readable messages distinguishing *process failure* from *process success with internal error/warning*, naming the invocation, transport, and `trace_id` | Must conform to the project's existing error-display convention: human-readable cause + path to `run.log`, never a stack trace in the terminal |
| `telemetry.jsonl` | New spans for external invocations (HTTP request lifecycle / subprocess lifecycle: launch, exit, duration), correlated to the run's `trace_id` | Extends the existing span shape; does not introduce a parallel telemetry format |
| `docs/specs/` (new schema docs) | New documented schemas (JSON Schema or equivalent) for the eight HTTP/script × task/judge × request/response payload shapes | Published alongside the existing `schema-configs.md` / `schema-outputs.md` so Builders find all schema references in one place |
| Eval `scripts/` directory | New scaffold starter file(s) materialized at eval-creation time for evals that opt into `external` execution | New convention — must be unmistakably marked as an editable starting point (not a generated artifact to leave alone, and not a fork of the canonical base class) |
| Per-invocation OS temp directory (script transport) | Created and destroyed automatically around each script invocation | Invisible in normal operation; only surfaces in logs when debugging a script-side problem (e.g., "response document missing in `<tmpdir>`") |

## Operator Flows

### Flow 1: Configure and run an `external` / `http` eval — skill-mediated (Platform Engineer)

1. Operator tells the skill, in their own words, "I want Gavel to run this eval against our internal HTTP service" (or similar). The skill identifies this as the §2 setup flow extended for non-`local` test subjects, orients itself by reading the (now-corrected) `references/config-schema.md`, and asks the operator the minimum it needs: endpoint, auth shape, and — new for this initiative — whether they want script-based execution instead, and what the desired halting behavior is for "the service doesn't respond" vs. "the service responds but flags its own problem."
2. The skill writes (or edits) `eval_config.json` on the operator's behalf: `test_subject_type: "external"`, `protocol: "http"`, the endpoint/method/headers/auth/trace-header config, and `abort_on_exec_failure`/`abort_on_process_error` — explaining each flag in the operator's vocabulary ("should the run stop if the service is unreachable?" / "should it stop if the service runs but reports a problem with its own answer?") rather than naming the flags cold. It shows the operator the resulting config block before running anything. (An optional `adapter` field also exists on this config, defaulting to `"gavel"`; the skill doesn't surface it unless the operator's service speaks something other than Gavel's own envelope — for this initiative, it never does, so the field stays invisible and today's experience is unchanged.)
3. The skill runs the eval (`gavel oneshot run --eval <name>`, per its existing §6 pattern). Gavel validates the config at run-start — a misconfigured field fails fast with a message naming the field and expected shape, before any HTTP calls are made; the skill relays this back in plain language and offers to fix it.
4. As the run proceeds, each invocation is logged with its `trace_id`, target endpoint, and outcome; `results_raw.jsonl` fills with real records (where today this path silently produces zero). The skill can summarize progress if asked.
5. At the end (or on a halting failure), the operator sees a run summary plus, for any issues, a Rich panel that names the tier — *"process failure: endpoint returned 503"* vs. *"completed with warning: response flagged validation issue"* — and points at `run.log` and the relevant `trace_id`. If the operator asks the skill to debug, it reads the panel/`run.log`, names the tier in plain language ("the service didn't respond" vs. "the service responded but flagged its own output"), and — per its existing §6 "Debug a run" role — points at the specific invocation and `trace_id` to inspect next.

**Alternate path:** Endpoint/auth is wrong in a way that only manifests per-call (e.g., a rejected token) rather than at config-validation time — the operator sees a stream of process-failure entries; with `abort_on_exec_failure=true` (default), the run halts on the first one with a message identifying the failing invocation's `trace_id` and the HTTP status/cause. The skill's job here is to *not* paraphrase this into something vaguer than the underlying message — it relays the tier and the specific cause, then helps the operator decide whether to fix the endpoint/auth or adjust the abort flag.

**Direct-config path (no skill):** An operator who prefers to hand-edit `eval_config.json` against `docs/specs/schema-configs.md` directly gets the identical validation, run, and error-classification behavior — the skill is a guided front door, not a different code path. This is also the default path for Systems-Under-Test Developers, who are more often reading schemas/scaffold code than asking the skill to write config for them.

### Flow 2: Configure and run an `external` / `script` eval — skill-mediated (ML Engineer)

1. Operator tells the skill "our scorer/judge only runs as a local script in a sandboxed environment — can Gavel call it?" The skill recognizes this as the `protocol: "script"` case, reads the corrected reference docs, and asks for the command/args, working directory, and timeout — and, as in Flow 1, walks the operator through the two abort flags in plain language.
2. The skill writes the config and explains, briefly, what will physically happen at run time (a per-invocation temp directory will be created, a request document written, the script launched, a response document read back, and the directory cleaned up automatically) — so the operator isn't surprised by log lines mentioning temp paths later.
3. The skill runs the eval. For each scenario, Gavel creates a per-invocation OS temp directory, writes a request document, launches the script, waits for a response document, reads it, and cleans up — all transparent to the operator in the success case. `results_raw.jsonl` fills with records in the same shape as HTTP or in-process runs; `run.log` shows per-invocation subprocess lifecycle (launch, exit code, duration) correlated to `trace_id`.
4. On completion, the operator (or the skill, if asked "did everything clean up?") can confirm via the run summary that no temp artifacts remain.

**Alternate path A — script crashes or times out:** classified as a process failure; `run.log` captures the exit code and stderr, the Rich panel names the cause ("script exited with code 1" / "script timed out after Ns"), and (with the default `abort_on_exec_failure=true`) the run halts. If the operator asks the skill to debug, it surfaces the exit code/stderr excerpt and frames it as "the script itself didn't complete" — distinct, in its phrasing, from the next two paths.

**Alternate path B — script completes but writes a malformed or missing response document:** also a process failure (FR-5.1), but the message — relayed faithfully by the skill, not softened — is specifically actionable for the *script author*: e.g., *"response document missing/invalid at `<path>` — see script task-response schema in `docs/specs/schema-external-runner.md`"*. The skill can hand the operator that exact schema reference to forward to whoever owns the script.

**Alternate path C — script completes and reports an internal warning** (e.g., "low confidence in this output"): classified as process success with warning; the record continues to flow into `results_raw.jsonl` with the warning attached, and (with the default `abort_on_process_error=false`) the run continues uninterrupted, with a `WARNING`-level log entry. If asked, the skill is explicit that this is *not* the same as a crash — "the script ran fine and flagged a low-confidence result; the run kept going because `abort_on_process_error` is off."

### Flow 3: Build a system-under-test from the scaffold (Systems-Under-Test Developer)

1. Developer is handed (or creates) an eval configured for `external`/`http` or `external`/`script`, and finds a scaffold starter file already present in the eval's `scripts/` directory.
2. Developer opens the file: it's a thin subclass stub of `RemoteSystemUnderTest` or `ScriptSystemUnderTest` with exactly one method to implement, plus inline comments pointing at (a) the documented request/response schema and (b) the canonical in-Gavel base class (so they know where the contract truly lives if Gavel's version changes).
3. Developer implements that one method, runs their service/script (standalone, or by re-running the eval), and the base class transparently handles request parsing/validation, log/telemetry-span emission correlated to the inbound `trace_id`, and response assembly (including the `status`/`issue` envelope).
4. Developer confirms success via the same `results_raw.jsonl`/log output the Platform/ML Engineer sees on the Gavel side — a working round trip looks like a normal successful run.

**Alternate path:** Developer's request handling raises (e.g., a field the developer expected isn't present, or Gavel's schema moved on). The base class surfaces a clear, schema-referencing error — naming the missing/mismatched field and the schema doc to check — rather than a generic deserialization stack trace, so the developer can self-diagnose without needing to read the base class's internals.

## States and Feedback

| State | Trigger | Operator Sees |
|-------|---------|---------------|
| **Start** | Run begins against an `external` test subject | Log line naming the protocol (`http`/`script`), target (endpoint or command), and the run's `trace_id` |
| **Progress** | Invocations in flight (HTTP calls or subprocess launches) | Per-invocation log entries (request sent / script launched, with `trace_id`), at a verbosity consistent with existing in-process LLM-call logging — informative, not flooding |
| **Success** | Invocation completes cleanly | `OutputRecord`/`JudgedRecord` populated and written; concise log entry with timing/status; (script) temp directory removed silently |
| **Warning** | Process success carrying an internal error/warning code, `abort_on_process_error=false` (default) | `WARNING`-level log entry naming the code/message and the invocation's `trace_id`; record continues into `results_raw.jsonl`/`results_judged.jsonl` with the issue attached; run continues |
| **Error (process failure)** | Non-2xx/unreachable/timeout (HTTP) or crash/timeout/malformed-response (script), `abort_on_exec_failure=true` (default) | Rich panel to stderr naming the tier explicitly ("process failure: …"), the cause, the invocation's `trace_id`, and a pointer to `run.log`; run halts — never a raw stack trace |
| **Error (process success, halting)** | Process success carrying an internal error/warning code, `abort_on_process_error=true` (operator-opted) | Same Rich-panel treatment as above, but the message makes clear the *external system ran fine* and *flagged its own problem* — distinct wording from a process failure so the operator isn't misled about where to look |
| **Misconfigured** | Invalid/missing `protocol` or protocol-specific config fields at run-start | Fail-fast validation error naming the offending field, the expected shape, and (for the `"in-situ"`→`"external"` rename) the old/new value mapping if applicable — surfaced before any invocation is attempted |

## Copy and Message Guidelines

- **The skill relays, it doesn't paraphrase away precision.** When `gavel-skill` surfaces an external-execution error/warning on the operator's behalf, it must preserve the tier name, the cause, and the `trace_id` verbatim (or near-verbatim) — translating *vocabulary* (Gavel internals → operator's mental model) is encouraged, but softening *which tier occurred* or *omitting the correlator* is not. The skill is a guided front door to the same precise messaging, not a different, vaguer one.
- **Name the tier explicitly.** Every external-execution error/warning message states whether it is a *process failure* ("the external system did not complete") or a *process success with an internal issue* ("the external system completed but flagged a problem") — operators must be able to act on the two-tier model from the message alone, without re-reading the PRD.
- **Always include the correlator.** Every external-execution log/error/warning message includes the invocation's `trace_id` (and, where relevant, the endpoint or script path) so the operator can pivot directly into `telemetry.jsonl` / `run.log` / the script's own logs.
- **Speak the operator's vocabulary, not Gavel's internals.** Use "endpoint", "script", "request", "response", "timeout", "exit code" — not `RemoteSystemInput`, `ProcessorResult`, or other internal type names — in operator-facing copy.
- **Stable, scriptable phrasing.** Prefixes and codes for the two tiers stay consistent across HTTP and script transports (e.g., a shared `process_failure` / `process_success_with_issue` vocabulary in logs and `OutputRecord.error`/`metadata`), so operators and tooling can grep/filter reliably.
- **No stack traces in the terminal.** Consistent with the existing convention (`docs` / CLAUDE.md "Error display"): human-readable cause + `run.log` pointer only.
- **Schema-referencing errors for scaffold/schema mismatches.** When a request/response fails to parse against a documented schema (Gavel-side or scaffold-side), name the specific field/section and the schema doc path — not a generic "validation failed."
- **Rename messaging (pending the Open Question on migration path):** if an alias-with-deprecation is chosen, the warning names both the old (`"in-situ"`) and new (`"external"`) values and points at the doc section to update; if a hard cutover is chosen, the validation error does the same, framed as a required fix rather than a warning.

## Accessibility and Readability

- **Terminal readability:** Plain-text-first messaging (no color-only signaling), consistent with the existing Rich-panel conventions that already degrade gracefully; keep line lengths reasonable for narrow terminals and CI log viewers.
- **Screen reader / editor readability:** New schema docs (`docs/specs/...`) and the scaffold starter file(s) use clear heading structure, descriptive field names, and short inline comments — they should read naturally both in an editor and via a screen reader, following the same documentation conventions as `schema-configs.md`/`schema-outputs.md`.
- **Machine readability:** `results_raw.jsonl` / `results_judged.jsonl` / `telemetry.jsonl` remain newline-delimited JSON with stable, additive field names (`trace_id`, `error`, `metadata`, `status`/`issue`); the eight documented payload schemas are machine-validatable (JSON Schema or equivalent) so CI and external-system tooling can check conformance automatically rather than relying on prose descriptions.
