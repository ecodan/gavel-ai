
---
summary: "Completes the stubbed `external`/`http` path (renamed from `in-situ`) by teaching `ScenarioProcessorStep` to build `RemoteSystemInput` objects for it, and adds a new `ScriptInputProcessor` for `protocol: 'script'` that exchanges JSON request/response documents through an auto-cleaned per-invocation OS temp directory. As part of the rename, `ClosedBoxInputProcessor`/`closedbox_processor.py` is renamed to `ExternalHttpProcessor`/`external_http_processor.py` to match the new terminology (ADR-8) — both processors live side-by-side with parallel naming. Both transports add `trace_id` to outbound payloads and (additively, via `metadata['trace_id']`) to `OutputRecord`/`JudgedRecord`; both route failures through `IssueClassifier`/`ErrorPolicy` using two new config-level flags (`abort_on_exec_failure` default true, `abort_on_process_error` default false) layered on top of the existing tier system. Eight JSON Schemas (http/script x task/judge x request/response) are published under `docs/specs/schema-external-runner.md`. Two scaffold base classes (`RemoteSystemUnderTest`, `ScriptSystemUnderTest`) live in `gavel_ai.scaffolds` and are optionally materialized into an eval's `scripts/` directory at creation time via the existing `gavel init`/eval-scaffolding path. The packaged `gavel-skill` (the Builder-facing 'Gavel Eval Assistant' and primary CX for configuration/debugging) gets its `references/config-schema.md`/`cli-reference.md` corrected (they currently document a stale `local|remote`/`acp|open_ai` shape) and extended to guide `external` setup and two-tier-failure debugging. Additionally reserves a forward-compatibility seam — an optional `adapter` field (default `'gavel'`) plus a transport/wire-format/classification structuring convention (ADR-10) — for a future front-door (native-protocol) testing initiative, with no MVP behavior change."
phase: "tech"
when_to_load:
  - "When implementing or reviewing scenario_processor.py routing changes, the new ScriptInputProcessor, trace_id propagation, two-tier error classification, the eight documented schemas, or the scaffold base classes."
  - "When checking whether implementation still conforms to the agreed architecture, interfaces, and conventions for external-runner."
depends_on:
  - "prd.md"
  - "operator-experience.md"
modules:
  - "src/gavel_ai/core/steps/scenario_processor.py"
  - "src/gavel_ai/core/steps/judge_runner.py"
  - "src/gavel_ai/processors/closedbox_processor.py -> external_http_processor.py (renamed, ADR-8)"
  - "src/gavel_ai/processors/script_processor.py (new)"
  - "src/gavel_ai/scaffolds/ (new — base classes)"
  - "src/gavel_ai/models/config.py (TestSubject, EvalConfig)"
  - "src/gavel_ai/models/runtime.py (RemoteSystemInput, ScriptSystemInput, OutputRecord, JudgedRecord)"
  - "src/gavel_ai/telemetry/ (spans.py, metadata.py)"
  - "docs/specs/schema-external-runner.md (new)"
  - "src/gavel_ai/skill/gavel-skill/ (SKILL.md, references/config-schema.md, references/cli-reference.md — correction + extension)"
index:
  overview: "## Overview & Context"
  stack: "## Tech Stack & Dependencies"
  structure: "## Project / Module Structure"
  adrs: "## Architecture Decisions (ADRs)"
  data_models: "## Data Models"
  interfaces: "## API & Interface Design"
  conventions: "## Implementation Patterns & Conventions"
  security_performance: "## Security & Performance"
  implementation_sequence: "## Implementation Sequence"
next_section: "Overview & Context"
---

# Tech Design: external-runner

## Progress

- [x] Overview & Context
- [x] Tech Stack & Dependencies
- [x] Project / Module Structure
- [x] Architecture Decisions (ADRs)
- [x] Data Models
- [x] API & Interface Design
- [x] Implementation Patterns & Conventions
- [x] Security & Performance
- [x] Implementation Sequence

---

## Overview & Context

**Summary:** This is a brownfield completion-plus-extension of Gavel's existing `Step` → `Processor` → `OutputRecord` pipeline. The `local` (prompt-based) path is the reference implementation: `ScenarioProcessorStep` builds typed `Input` objects (`PromptInput`), hands them to a `Processor` (`PromptInputProcessor`) via an `Executor`, and converts each `ProcessorResult` into an `OutputRecord`. The `external`/`http` path already has a working processor (today named `ClosedBoxInputProcessor`, accepting `RemoteSystemInput` — renamed to `ExternalHttpProcessor` as part of this initiative, see ADR-8) — but `ScenarioProcessorStep` never builds those inputs, so `inputs` stays `[]` and the path silently produces zero records (`scenario_processor.py:175-214`, gated to `test_subject_type == "local"`). The architecture, therefore, is: **(1)** extend the existing routing/input-building logic to cover `external`/`http`, **(2)** add a new `ScriptInputProcessor` + `ScriptSystemInput` that slot into the *same* pipeline for `external`/`script`, **(3)** thread `trace_id` through both, **(4)** layer two new abort flags onto the existing `IssueClassifier`/`ErrorPolicy` machinery, **(5)** publish schemas, **(6)** ship scaffold base classes for the systems on the other end of the wire, and **(7)** correct and extend `gavel-skill`'s reference docs and conversational flows — the primary CX through which most Builders will reach this feature (see Overview note in `operator-experience.md`). No new pipeline architecture is introduced — every new piece is a `Processor`/`Input`/`OutputRecord` that the existing `Executor`/`Step` machinery already knows how to drive.

### Cross-Cutting Concerns

1. **Pipeline-contract conformance** — every new component (`ScriptInputProcessor`, the renamed routing branch) must produce the exact same `ProcessorResult` → `OutputRecord` shape the rest of the system (judges, reporters, reflection) already consumes. This is the single biggest constraint on every design choice below; it is what keeps this a "complete + extend" effort instead of a parallel system.
2. **Two-tier error classification routes through `IssueClassifier`/`ErrorPolicy`, not around it** — `classify`/`classify_message`, `Step.safe_execute`, and `error_policy.should_halt(tier)` are the existing halting primitives (per CLAUDE.md: "do not duplicate the expression inline"). The two new abort flags (`abort_on_exec_failure`, `abort_on_process_error`) must resolve to a `tier` (`ERROR`/`WARNING`/`OK`) that flows through that exact same machinery — see ADR-3.
3. **`trace_id` propagation must be additive** — `OutputRecord`/`JudgedRecord` are consumed by reporters, schema validators, and (per Open Question in `prd.md`) potentially other tooling. Adding `trace_id` cannot be a breaking schema change — see ADR-2.
4. **The skill's reference docs are the de facto onboarding contract** — `gavel-skill` orients itself by reading `references/config-schema.md`/`cli-reference.md` before advising a Builder (`SKILL.md` §0). Those docs are *already* stale relative to the real `TestSubject`/`EvalConfig` shape (`local|remote`/`acp|open_ai` vs. reality's `local`/`in-situ→external`/free-text `protocol`) — a pre-existing defect this initiative must fix as a precondition, not a courtesy, since the skill cannot correctly guide *any* non-`local` setup (including the new `external` path) while reading wrong references. See ADR-9.

### Brownfield Notes

- **Touches**: `scenario_processor.py` (routing + input-building), `judge_runner.py` / `JudgeExecutor` (delegation), `models/config.py` (`TestSubject`, new flags), `models/runtime.py` (new `ScriptSystemInput`, additive `OutputRecord`/`JudgedRecord` fields), `telemetry/` (read-only — consumes `get_current_run_id()`/tracer, does not change span format), `processors/` (renamed `ExternalHttpProcessor`, new `ScriptInputProcessor`, new `scaffolds/` package), `skill/gavel-skill/` (reference-doc correction + extension).
- **Must NOT change**: `PromptInputProcessor`/`local` path behavior or output shape (zero regressions — explicit Quality Gate in `prd.md`); the `Processor`/`ProcessorResult`/`Executor` interfaces; `IssueClassifier`/`ErrorPolicy` halting semantics for existing tiers.
- **Existing patterns this design follows**: `ClosedBoxInputProcessor`'s (→ `ExternalHttpProcessor`'s) constructor signature (`config: ProcessorConfig, **kwargs`) and its use of `get_tracer(__name__)`; `ScenarioProcessorStep`'s per-variant processor instantiation and `_spool_result`/`executor.execute(inputs, on_result=...)` flow; `JudgeRunnerStep`'s `_load_markdown_judge_config` path-traversal guard pattern (directly reusable for confining script I/O to the temp dir — see ADR-5); the project's `Annotated[Optional[str], typer.Option(...)] = None` CLI pattern, if a scaffold-materialization CLI surface is added; `gavel-skill`'s existing `scripts/update_cli_reference.py`-style self-maintenance convention, as a model for keeping its references accurate going forward.

---

## Tech Stack & Dependencies

| Category | Selection | Rationale |
|----------|-----------|-----------|
| **Language/Runtime** | Python 3.13+ (existing) | No change — matches project baseline |
| **HTTP client** | `httpx.AsyncClient` (existing, via `ExternalHttpProcessor`, renamed from `ClosedBoxInputProcessor` per ADR-8) | Already in use; no new HTTP dependency needed for the completed `external`/`http` path |
| **Subprocess execution** | `asyncio.create_subprocess_exec` (stdlib) | Argument-list form avoids shell-injection by construction (no `shell=True`); async-native, integrates with existing `asyncio`-based `Executor`/`async_config` |
| **Temp directories** | `tempfile.TemporaryDirectory` (stdlib) | Auto-cleanup on context-manager exit (success or exception) satisfies FR-3.2 with no custom cleanup logic to get wrong |
| **Schema publication** | Pydantic `model_json_schema()` exported to static JSON files under `docs/specs/` | Reuses existing Pydantic models as the single source of truth — schemas can't drift from the models that produce/consume them; avoids hand-maintained JSON Schema files |
| **Tracing** | `gavel_ai.telemetry.get_tracer` / `get_current_run_id` (existing) | No new tracing dependency — reuses the exact OTEL setup `ExternalHttpProcessor` already uses |
| **Testing** | `pytest`, `pytest.mark.unit` / `pytest.mark.integration` (existing) | Matches `tests/unit` / `tests/integration` layout; script-processor tests use real `tempfile` dirs and a real (trivial) subprocess per [[feedback_real_tests]] convention — no `MagicMock` of the filesystem or subprocess |

**New dependencies introduced:** None. Everything above is either already a project dependency or stdlib.

**Dependencies explicitly rejected:**
- `subprocess.run(..., shell=True)` — shell-injection risk; argument-list `asyncio.create_subprocess_exec` achieves the same outcome safely.
- A new JSON Schema authoring library (e.g. hand-written `.schema.json` + a validator) — Pydantic's `model_json_schema()` keeps schema and model in lockstep; hand-written schemas would be a second source of truth that drifts.
- `watchdog`/filesystem-event libraries for detecting the script's response document — adds a dependency and an event loop integration burden for something a simple post-exit read accomplishes (the script signals completion by exiting; Gavel reads the response document only after the process exits — see ADR-4).

---

## Project / Module Structure

```
src/gavel_ai/
├── core/steps/
│   └── scenario_processor.py         # [MODIFIED] routes "external"/{http,script} to the right processor + input builder
├── processors/
│   ├── external_http_processor.py    # [RENAMED from closedbox_processor.py, ADR-8] adds trace_id header
│   │                                  #   injection + two-tier classification (ADR-3); class ExternalHttpProcessor
│   ├── script_processor.py           # [NEW] ScriptInputProcessor — temp-dir handoff, subprocess lifecycle
│   └── base.py                       # unchanged — InputProcessor ABC
├── scaffolds/                         # [NEW] package — base classes for systems-under-test
│   ├── __init__.py                   # exports RemoteSystemUnderTest, ScriptSystemUnderTest
│   ├── base.py                       # shared validation/telemetry/response-assembly logic (ADR-6)
│   ├── remote.py                     # RemoteSystemUnderTest (HTTP-side base class)
│   ├── script.py                     # ScriptSystemUnderTest (script-side base class)
│   └── _materialize.py               # copies a scaffold template into an eval's scripts/ dir (ADR-7)
├── models/
│   ├── config.py                      # [MODIFIED] TestSubject: protocol "http"|"script", abort flags, protocol config
│   └── runtime.py                     # [MODIFIED] new ScriptSystemInput; additive OutputRecord/JudgedRecord trace_id
└── telemetry/                         # unchanged — consumed via get_tracer/get_current_run_id

docs/specs/
└── schema-external-runner.md          # [NEW] documents + links the eight generated JSON Schemas

src/gavel_ai/skill/gavel-skill/
├── SKILL.md                           # [MODIFIED] setup/debug flows extended for external/{http,script}
└── references/
    ├── config-schema.md               # [MODIFIED — corrects stale local|remote/acp|open_ai documentation]
    └── cli-reference.md               # [MODIFIED if external-specific CLI behavior needs documenting]

{eval_dir}/scripts/
└── {scaffold_name}.py                 # [NEW, materialized at eval-creation time] editable starter subclass
```

**Key structural decisions:**
- The new `ScriptInputProcessor` lives beside the renamed `ExternalHttpProcessor` in `processors/`, not in a new top-level package — it is a `Processor` like any other, and `ScenarioProcessorStep` already knows how to drive processors uniformly. Parallel naming (`ExternalHttpProcessor` / `ScriptInputProcessor` — both communicating "external execution, transport X") replaces the old "closed-box" framing the rename is explicitly retiring (ADR-8).
- Scaffold base classes get their **own package** (`scaffolds/`) rather than living in `processors/`: they run *inside the system-under-test's process*, not Gavel's pipeline, and importing them must not pull in Gavel's runtime/pipeline dependencies. This separation is itself a documented contract boundary (see ADR-6).
- `_materialize.py` is intentionally a thin, separate module — it's filesystem/templating glue invoked at eval-creation time, not part of the runtime hot path, and keeping it isolated makes it easy to test independently and to swap mechanisms later (Open Question in `prd.md`).

---

## Architecture Decisions (ADRs)

### ADR-1: Routing change is additive to `ScenarioProcessorStep`, not a rewrite

**Decision:** Extend the existing `if eval_config.test_subject_type == "local": ... build PromptInput` block (and the `processor_type` selection at `scenario_processor.py:247-249`) with parallel branches for `"external"` + `protocol == "http"` (build `RemoteSystemInput`, reuse `ExternalHttpProcessor`) and `"external"` + `protocol == "script"` (build `ScriptSystemInput`, use the new `ScriptInputProcessor`). The existing per-variant loop, `_spool_result`, `Executor`, and `_make_output_record` flow are reused unchanged.

**Rationale:** The stub bug is a *missing branch*, not a *wrong architecture* — `ExternalHttpProcessor` already returns conformant `ProcessorResult`s. Rewriting the step risks regressing the working `local` path (an explicit non-goal / quality gate). Minimal-diff extension is also easiest to review and test incrementally (HTTP branch first, since it's "complete a stub," then script branch, which is net-new).

**Affects:** `scenario_processor.py` (`execute()`, input-building block, `processor_type` resolution); no changes to `Executor`, `_make_output_record`, or `_spool_result`.

---

### ADR-2: `trace_id` lands in `OutputRecord.metadata["trace_id"]`, not as a first-class field

**Decision:** Resolve the Open Question from `prd.md` in favor of the additive option: `trace_id` is written to `metadata["trace_id"]` on `OutputRecord` and `JudgedRecord` (both gain it — `JudgedRecord` currently has no `metadata` field, so this requires adding one, additively, with `default_factory=dict`). `docs/specs/schema-outputs.md` documents the key as present-when-externally-executed.

**Rationale:** `OutputRecord`/`JudgedRecord` are `extra="ignore"` Pydantic models consumed by reporters and schema validators; a new required or even `Optional` *first-class* field changes the schema surface every consumer (including ones outside this initiative's test coverage, e.g. reporter Jinja2 templates) must tolerate. A `metadata` key is zero-risk-additive — exactly the pattern `_make_output_record` already uses for `template`/`scenario_input`/turn data — and is consistent with how `trace_id`/`run_id` attributes already live as span *attributes* (not first-class span fields) in `telemetry/spans.py`. The minor cost (slightly less discoverable than a top-level field) is mitigated by documenting the key explicitly and giving it a stable, predictable name.

**Consequences:** Joining `results_raw.jsonl` rows to `telemetry.jsonl` spans requires reading `metadata["trace_id"]` rather than a top-level column — acceptable, and consistent with how `metadata["turn_number"]` etc. are already joined today. If a future initiative promotes `trace_id` to first-class on *all* records (in-process included), that's an additive migration on top of this, not a breaking one.

**Affects:** `_make_output_record` (`scenario_processor.py`), `JudgedRecord` (add `metadata: Dict[str, Any] = Field(default_factory=dict)`), `judge_runner.py` (populate it for external judge delegation), `docs/specs/schema-outputs.md`.

---

### ADR-3: Two-tier classification is implemented as a *mapping function* feeding the existing `IssueClassifier`/`ErrorPolicy`, not a parallel halting path

**Decision:** Add a small pure function, `classify_external_outcome(outcome: ExternalOutcome, abort_on_exec_failure: bool, abort_on_process_error: bool) -> Tier`, where `ExternalOutcome` is a 2-value enum (`PROCESS_FAILURE`, `PROCESS_SUCCESS_WITH_ISSUE`) determined by the processor from transport-specific signals (HTTP status / response envelope `status` field; subprocess exit code / response-document presence / response envelope `status` field). The function returns `Tier.ERROR` or `Tier.WARNING` per the flag values (mirroring `IssueClassifier`'s existing `Tier` vocabulary), and the *existing* `error_policy.should_halt(tier)` / `Step.safe_execute` / `RunPolicyError` path does the actual halting — identical to how `_spool_result` already calls `classify_message(result.error)` today (`scenario_processor.py:291-296`).

**Rationale:** This is the only design that satisfies CLAUDE.md's explicit instruction to "Use `error_policy.should_halt(tier)` for the halt predicate — do not duplicate the expression inline," while still letting the two new flags (which `ErrorPolicy` doesn't natively know about) influence the outcome. The mapping function is the seam: it translates *external-runner-specific* signals into the *existing* `Tier` vocabulary, then gets out of the way.

**Consequences:** `abort_on_exec_failure`/`abort_on_process_error` live on `TestSubject` (and external judge config), not on `ErrorPolicy` — `ErrorPolicy` remains transport-agnostic. The mapping function is unit-testable in isolation (4 flag-combination × 2 outcome-type matrix = 8 cases) without spinning up a processor.

**Affects:** New `core/issue_classifier.py` helper (or a sibling module — placement TBD at implementation time, but logically belongs beside `classify`/`classify_message`); `ExternalHttpProcessor`/`ScriptInputProcessor` (call it and surface the result via `ProcessorResult.error`/`metadata`); `_spool_result` (already calls `classify_message` — needs to also recognize externally-pre-classified outcomes so it doesn't re-derive the tier from a string).

```python
class ExternalOutcome(str, Enum):
    PROCESS_FAILURE = "process_failure"
    PROCESS_SUCCESS_WITH_ISSUE = "process_success_with_issue"

def classify_external_outcome(
    outcome: Optional[ExternalOutcome],
    abort_on_exec_failure: bool,
    abort_on_process_error: bool,
) -> Tier:
    """Map a transport-observed outcome + Builder flags onto the existing Tier vocabulary."""
    if outcome is None:
        return Tier.OK
    if outcome is ExternalOutcome.PROCESS_FAILURE:
        return Tier.ERROR if abort_on_exec_failure else Tier.WARNING
    return Tier.ERROR if abort_on_process_error else Tier.WARNING
```

---

### ADR-4: Script handoff is a synchronous "launch → await exit → read response" cycle, not a polling/watch pattern

**Decision:** `ScriptInputProcessor` writes the request document, launches the subprocess via `asyncio.create_subprocess_exec(*command_and_args, cwd=tmpdir)`, `await`s its completion (subject to `async_config.task_timeout_seconds` via `asyncio.wait_for`), and *only then* attempts to read the response document. A non-zero exit code or a missing/unparseable response document is classified as `PROCESS_FAILURE` regardless of what (if anything) was written.

**Rationale:** The script signals "I'm done" by exiting — this is the simplest, most portable completion signal across languages/runtimes (no polling interval to tune, no filesystem-watcher dependency, no race between "file exists" and "file fully written"). It mirrors how the HTTP path already treats "response received" as the completion signal. Exit-then-read also makes the temp-directory lifecycle trivially scoped to a single `async with tempfile.TemporaryDirectory() as tmpdir:` block (FR-3.2), which is what makes auto-cleanup-on-any-outcome free.

**Consequences:** Long-running "the script starts a job and reports later" patterns are explicitly out of scope for v1 (already captured as a v2 Growth Feature — "poll-for-completion" — in `prd.md`). Timeout handling: on `asyncio.TimeoutError`, terminate the process (`SIGTERM`, then `SIGKILL` after a short grace period — resolves the Open Question in `prd.md` in favor of the standard graceful-then-forceful pattern already implied by `async_config.task_timeout_seconds` semantics elsewhere) and classify as `PROCESS_FAILURE`.

**Affects:** `script_processor.py` (`process()` method); `async_config.task_timeout_seconds` consumption; stderr capture (`asyncio.subprocess.PIPE`, captured into `ProcessorResult.metadata["stderr"]` for failure diagnostics, truncated to a bounded length to avoid log/record bloat).

---

### ADR-5: All script I/O is confined to the per-invocation temp directory via the same path-confinement check `judge_runner.py` already uses

**Decision:** Request and response document paths are always `Path(tmpdir) / "request.json"` and `Path(tmpdir) / "response.json"` (configurable *filenames* via `TestSubject.config`, per FR-1.2, but never configurable *directories*). Before reading the response document, resolve it and assert it is contained within the resolved `tmpdir`, using the identical `resolved.startswith(eval_dir_resolved)` pattern `_load_markdown_judge_config` already implements (`judge_runner.py:~70-75`) — adapted to the temp-dir boundary instead of the eval-dir boundary.

**Rationale:** This is a direct reuse of an existing, reviewed security pattern in the same codebase rather than inventing a new one — satisfying both "Brownfield first: don't introduce new patterns" and the Security NFR's "no Builder-supplied path traversal." Fixing the directory (only filenames are configurable) eliminates an entire class of misconfiguration (a Builder accidentally pointing the response path outside the sandbox).

**Affects:** `script_processor.py` (request/response path construction + confinement check); `TestSubject.config` schema for `protocol: "script"` (documents that only filenames, not paths, are configurable).

---

### ADR-6: Scaffold base classes are split Gavel-side (schema/telemetry helpers) vs. transport-side (HTTP server glue / script entrypoint glue), unified by a shared `_BaseSystemUnderTest` mixin

**Decision:** `scaffolds/base.py` defines a `_BaseSystemUnderTest` mixin providing the three transport-agnostic capabilities from FR-8.2 — request parsing/validation against the documented Pydantic models (reusing the *same* models that generate the JSON Schemas — see Tech Stack), `trace_id`-correlated log/span emission (via a thin wrapper that mirrors `telemetry/spans.py` conventions but targets the *external system's own* OTEL/log sink — see Open Question resolution below), and `status`/`issue` envelope assembly. `RemoteSystemUnderTest` (in `remote.py`) and `ScriptSystemUnderTest` (in `script.py`) each add only the transport glue (an HTTP handler entrypoint vs. a `main()` that reads/writes the temp-dir documents) and require the subclass to implement exactly one method: `handle(request: TaskOrJudgeRequest) -> TaskOrJudgeResult`.

**Rationale:** FR-8.3 requires "implement only one method" — that's only achievable if all schema/telemetry/assembly logic is shared and transport-specific glue is minimal and pre-written. A mixin avoids duplicating the FR-8.2 logic between the two base classes (the alternative — two independent base classes — would let them drift from each other, the exact failure mode FR-8 exists to prevent).

**Telemetry contract (resolves the matching Open Question):** the mixin emits structured JSON log lines (matching `LOG_FORMAT`/`create_logger` conventions from CLAUDE.md) *and*, when an OTEL collector endpoint is configured (via an optional constructor/env parameter — the system-under-test may run in a different environment than Gavel), standard OTEL spans carrying the inbound `trace_id` as a span attribute (mirroring, not reusing, `telemetry/spans.py`'s attribute-naming convention — the scaffold cannot import Gavel's run-scoped `TelemetryFileExporter` because it doesn't have a `run_id`/eval directory). This is "mirror the convention, don't share the implementation," documented explicitly in the scaffold's module docstring.

**Affects:** `scaffolds/base.py`, `scaffolds/remote.py`, `scaffolds/script.py`; the documented schemas (FR-6) become the Pydantic models the mixin validates against — single source of truth shared with schema generation (Tech Stack decision).

---

### ADR-7: Scaffold materialization is a copy-with-version-marker into `scripts/`, triggered at eval-creation time through the existing `gavel init`-style scaffolding surface

**Decision:** `scaffolds/_materialize.py` exposes a function that copies the appropriate scaffold template (selected by the eval's configured `protocol`) into `{eval_dir}/scripts/{name}_scaffold.py`, with a header comment block recording the source module path and a content hash/version marker of the canonical class it was copied from (resolving the drift-detection mitigation from `prd.md`'s Risk Mitigation table). It is invoked from wherever eval directories are currently scaffolded (the same code path `gavel init` / eval-creation already uses to lay down `eval_config.json`, `scenarios.jsonl`, etc.) — *only* when the new eval's `test_subject_type` is configured as `"external"`.

**Rationale:** Materializing at eval-creation time (rather than via a standalone `gavel scaffold` subcommand) means a Builder configuring an `external` eval gets the starter file exactly when and where they need it, with zero extra steps — directly satisfying the Journey 3 narrative ("finds it pre-populated"). Piggybacking on the existing eval-scaffolding path (rather than inventing a new CLI surface) is the minimal-new-surface option and follows "Brownfield first." The version-marker header is a few lines of comment, not a build-system feature — cheap insurance against the drift risk.

**Consequences:** If a Builder changes `test_subject_type` to `"external"` *after* eval creation, they don't automatically get the scaffold — this is acceptable for v1 (documented as a known gap; a future `gavel scaffold add` on-demand command is a natural v2 extension, not blocking MVP).

**Affects:** `scaffolds/_materialize.py`; the eval-creation/`gavel init` code path (one new conditional call); scaffold template files (one per protocol, stored alongside the canonical base classes per the existing `package_data` convention — `[tool.setuptools.package-data] gavel_ai = [...]` already covers `reporters/templates/*`, extend it to cover `scaffolds/templates/*`).

---

### ADR-8: Rename `ClosedBoxInputProcessor`/`closedbox_processor.py` → `ExternalHttpProcessor`/`external_http_processor.py`

**Decision:** As part of the `test_subject_type`/`protocol` terminology rename (FR-1.1), also rename the class `ClosedBoxInputProcessor` → `ExternalHttpProcessor` and its file `processors/closedbox_processor.py` → `processors/external_http_processor.py`, updating every reference (imports, `scenario_processor.py` instantiation, `report_runner.py`, `processors/__init__.py`, `models/config.py`/`runtime.py` docstrings, the test files `tests/unit/processors/test_closedbox_processor.py` → `test_external_http_processor.py` and `tests/integration/test_processor_chain_e2e.py`, and the private design docs under `docs/.private/` that reference it). The class's public interface, constructor signature, and internal logic are otherwise untouched — this is a rename, not a rewrite (ADR-1 already establishes that the *behavior* is reused as-is).

**Rationale:** The PRD is explicitly retiring "closed-box"/"in-situ" framing in favor of "external" (FR-1.1, Executive Summary "What Makes This Special"). Leaving the class that *implements* the `external`/`http` transport named after the terminology being retired creates exactly the code/concept mismatch the Future-Maintainer review persona would flag immediately ("why is the `external` processor called `ClosedBox`?"). Renaming now — while the class is already being modified for `trace_id`/two-tier-classification (ADR-2/ADR-3) — means the rename rides along on a diff that's touching the file anyway, rather than becoming a separate, harder-to-justify-in-isolation change later. `grep -rl "closedbox\|closed.box\|closed_box"` currently surfaces ~14 files (8 source/test, 6 private docs) — a bounded, mechanically-verifiable rename.

**Consequences:** Slightly enlarges the diff for what would otherwise be a narrowly-scoped processor change — but the alternative (an `external` system whose implementation class is named `ClosedBox`) is a permanent naming inconsistency, strictly worse long-term. `RemoteSystemInput` (the `Input` model `ExternalHttpProcessor` consumes) is *not* renamed — its name is generic enough to remain accurate (it represents "input destined for a remote system" regardless of what the processor that consumes it is called), and renaming it would unnecessarily widen the diff into `models/runtime.py` call sites that don't need to change.

**Affects:** `processors/closedbox_processor.py` → `external_http_processor.py` (class `ClosedBoxInputProcessor` → `ExternalHttpProcessor`); `processors/__init__.py`; `scenario_processor.py` import + instantiation (`scenario_processor.py:271`); `report_runner.py`; `tests/unit/processors/test_closedbox_processor.py` → `test_external_http_processor.py`; `tests/integration/test_processor_chain_e2e.py`; docstring/comment references in `models/config.py`, `models/runtime.py`.

---

### ADR-9: Correct and extend `gavel-skill`'s reference docs as a blocking precondition, not a follow-on doc task

**Decision:** Update `src/gavel_ai/skill/gavel-skill/references/config-schema.md` to replace its stale `test_subject_type: "local" | "remote"` / `protocol: "acp" | "open_ai"` documentation with the real, current shape — `"local" | "external"` (post-rename) and the actual per-protocol `config` sub-shapes this initiative defines (FR-1.2) — and extend `SKILL.md`'s setup flow (§2) and debugging guidance (§6) to cover `external`/`http`|`script` configuration and two-tier-failure interpretation, in the operator vocabulary defined in `operator-experience.md` (Copy and Message Guidelines). Sequence this as part of **Foundation** (Implementation Sequence step 1 / alongside step 2), not as a trailing documentation pass.

**Rationale:** `SKILL.md` §0 instructs the assistant to read these references *before* advising a Builder — they are not optional background reading, they are the assistant's working knowledge. They are *already wrong* (documenting a `local|remote`/`acp|open_ai` shape that doesn't match the real `TestSubject` model), which means the skill cannot correctly help with **any** non-`local` test subject today, including the currently-stubbed `in-situ`/`external` path this initiative completes. Fixing them is therefore a precondition for the skill to be able to do its job at all for this feature — sequencing it late would mean shipping a working `external` path that the project's own primary-CX assistant cannot correctly explain.

**Consequences:** Slightly grows the "Foundation" slice of work (doc correction + extension alongside model/type changes) — but it's the cheapest point to do it: the same engineer making the `TestSubject`/`protocol` model changes (Implementation Sequence step 1) is best positioned to also correct the doc that describes that exact shape, while the mapping is freshest in mind. Bundling avoids a second context-load of the same model surface later.

**Affects:** `skill/gavel-skill/references/config-schema.md` (corrected `test_subject_type`/`protocol`/`config` documentation); `skill/gavel-skill/SKILL.md` (§2 setup flow, §6 debug flow extended for `external`); `skill/gavel-skill/references/cli-reference.md` (only if `external`-specific CLI behavior — e.g., new flags or output — needs documenting; likely minimal, since execution still goes through `gavel oneshot run`).

---

### ADR-10: Reserve an `adapter` field and a transport/wire-format seam for future front-door (native-protocol) testing — additive, no MVP behavior change

**Decision:** This initiative ships only Gavel's own bespoke envelope (`ExternalTaskRequest`/`ExternalResponseEnvelope`, the "side door" — the tested service must implement Gavel's glue). A near-future follow-on initiative will add "front door" testing — calling a service through the wire protocol it *already* speaks to real users (e.g. OpenAI chat-completions JSON), with no Gavel-specific glue required on the service side. To keep that follow-on an additive sibling rather than a refactor of shipped, tested code, this initiative reserves a clean seam now, in three parts:
1. **Architectural seam — separate "transport" from "wire format/envelope."** `ExternalHttpProcessor` and `ScriptInputProcessor` internally factor "send/receive over the wire" apart from "build the outbound payload" and "parse the inbound response into `ExternalOutcome`/`OutputRecord`," even though only one wire format (Gavel's own envelope) ships in this MVP. The next initiative then adds a sibling adapter beside the shipped one, instead of refactoring a shipped processor.
2. **New optional config field, not a composite string.** Add `adapter: Optional[str] = "gavel"` to `TestSubject` (and the equivalent judge-config shape), orthogonal to `protocol: "http" | "script"`. `protocol` stays exactly as designed — the transport axis (how bytes move). `adapter` is the new wire-format axis (what shape the payload is). When `adapter` is omitted, MVP behavior is unchanged — `"gavel"` is the only implemented adapter.
3. **Classification & correlation structured to be adapter-keyed, not envelope-hardcoded.** `classify_external_outcome` and `trace_id` round-trip correlation currently assume Gavel's envelope shape (`status`/`issue`/`trace_id` fields). Write the mapping function/strategy so it is parameterizable by adapter — even though only one parameterization (Gavel's) exists today — so a future OpenAI-shaped adapter can supply its own classification mapping (e.g. classify on HTTP status + `error` object + `finish_reason`, with header-only/best-effort `trace_id` correlation as an accepted, documented degraded mode, since such payloads typically cannot carry `trace_id` in-body).

**Rationale:** The Builder flagged a real gap: the shipped `external` path only supports a "side door." Reserving the seam now — while `ExternalHttpProcessor`/`ScriptInputProcessor`/`classify_external_outcome` are already being modified for `trace_id`/two-tier classification (ADR-2/ADR-3) — costs little (it's a structuring convention applied to code already being touched) and avoids a much costlier refactor of shipped, tested code later. A composite-string encoding (`protocol: "http[gavel]"` / `"http[openai]"`) was explicitly rejected: it would require a custom parse/serialize/validate layer that a clean two-field Pydantic model doesn't need. Two independent typed fields validate independently, and a future "is `script` + `openai_chat` even sensible?" check is a normal model validator, not string-splitting logic. No rename of `protocol` values is needed — `"http"`/`"script"` remain transport-family names; `adapter` carries the wire-format identity, so there's no future collision between the two axes.

**Consequences:** This is forward-compatibility runway, not new MVP scope — no new adapter ships, no new processor branch is added, and Builder-visible behavior is unchanged when `adapter` is omitted (the default `"gavel"` preserves exactly today's envelope-based behavior). The cost is borne entirely as "structure the code you're already writing to be extension-ready" — e.g., a private `_build_payload`/`_parse_response`/`_classify` seam inside each processor and a strategy/mapping-table shape for `classify_external_outcome` keyed by `adapter` — rather than as additional deliverables, tests, or partitions. The next initiative's job becomes "add a sibling adapter module and register it," not "refactor `ExternalHttpProcessor`."

**Affects:** `models/config.py` (`TestSubject.adapter: Optional[str] = "gavel"`, additive/optional); `processors/external_http_processor.py` and `processors/script_processor.py` (internal transport/payload-building/response-parsing seam, no change to external interface or `ProcessorResult` shape); `core/issue_classifier.py` (or sibling module) — `classify_external_outcome` structured as adapter-parameterizable, with the Gavel mapping as the sole registered parameterization; `docs/specs/schema-external-runner.md` (documents `adapter` and notes the reserved seam for future wire formats).

---

## Data Models

### New Models

```python
# models/runtime.py — additive

class ScriptSystemInput(Input):
    """Input for script/process-based external execution.

    Represents a single script invocation: the command to launch and the
    fully-specified request payload to write to the request document before
    launch. Mirrors RemoteSystemInput's role for the http transport.
    """
    model_config = ConfigDict(extra="ignore")

    command: List[str] = Field(..., description="Argument-list command (no shell interpolation)")
    working_dir: Optional[str] = Field(None, description="Working directory override")
    request_payload: Dict[str, Any] = Field(..., description="Fully-specified request document content")
    request_filename: str = Field("request.json", description="Request document filename within the temp dir")
    response_filename: str = Field("response.json", description="Response document filename within the temp dir")


class ExternalIssue(BaseModel):
    """Structured error/warning envelope shared by both transports' response schemas (FR-6.3)."""
    model_config = ConfigDict(extra="ignore")

    code: str = Field(..., description="Stable, documented issue code")
    level: Literal["error", "warning"] = Field(..., description="Issue severity")
    message: str = Field(..., description="Human-readable description")


class ExternalResponseEnvelope(BaseModel):
    """Top-level shape of every task/judge response payload, both transports (FR-6.3).

    `status: "ok"` with `issue` present => process success with internal issue (ADR-3 PROCESS_SUCCESS_WITH_ISSUE).
    `status: "error"` => process failure (ADR-3 PROCESS_FAILURE) — typically only reachable
    on the script transport where the process completed but self-reported failure
    (HTTP process failures are signaled by status code, not this envelope).
    """
    model_config = ConfigDict(extra="ignore")

    status: Literal["ok", "error"] = Field(..., description="Top-level outcome status")
    result: Optional[Dict[str, Any]] = Field(None, description="Scenario result content (task output or judge score/reasoning)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="timing_ms, turns, custom fields")
    issue: Optional[ExternalIssue] = Field(None, description="Present when status carries an error/warning")
    trace_id: Optional[str] = Field(None, description="Echo of the inbound trace_id, for correlation/debugging on the system-under-test side")
```

**Key field decisions:**
- `ScriptSystemInput.command` is `List[str]` (not `str`) — enforces argument-list invocation at the type level (ADR-5/Security NFR); a `str` would invite `.split()` footguns or `shell=True` workarounds.
- `request_filename`/`response_filename` are configurable strings (not paths) — the directory is always the per-invocation temp dir (ADR-5); this is enforced by type (filenames only) plus a runtime confinement check.
- `ExternalResponseEnvelope.status`/`issue` is the single `status: "ok"|"error"` + optional `issue: {code, level, message}` shape the PRD specified (FR-6.3) — it is the *one* piece of the response schema both transports share verbatim, and it's what `classify_external_outcome` (ADR-3) reads to determine `ExternalOutcome`.

### Modified Models

| Model | Change | Migration Required? |
|-------|--------|-------------------|
| `TestSubject` | `protocol: Optional[str]` → constrained to `Literal["http", "script"]` when `test_subject_type == "external"`; add `abort_on_exec_failure: bool = True`, `abort_on_process_error: bool = False`; add `adapter: Optional[str] = "gavel"` (new, orthogonal wire-format axis reserved for future front-door adapters — see ADR-10; `"gavel"` is the only implemented value, omitting it preserves current behavior exactly); `config: Dict[str, Any]` gains protocol-specific documented sub-shapes (endpoint/method/headers/auth/trace-header for `http`; command/args/working_dir/timeout/filenames for `script`) | Additive (new optional fields with defaults) — no migration for the fields themselves. The `test_subject_type` value rename (`"in-situ"` → `"external"`) is the migration-relevant change — see below. |
| `EvalConfig.test_subject_type` | Accepts `"external"` as a valid value; `"in-situ"` handling resolved per the chosen migration path (see Schema/Migration Notes) | **Yes** — config-level value rename; needs an explicit decision (alias-with-deprecation-warning vs. hard cutover) before implementation, currently an Open Question in `prd.md` |
| `OutputRecord` | No field change — `metadata["trace_id"]` populated for external executions (ADR-2) | No — purely additive use of an existing `Dict[str, Any]` field |
| `JudgedRecord` | **Add** `metadata: Dict[str, Any] = Field(default_factory=dict)` (currently absent) | Additive — new optional field with a safe default; existing `extra="ignore"` consumers unaffected |

### Schema / Migration Notes

- **Recommended migration path** (to resolve the Open Question, pending Builder sign-off): treat `"in-situ"` as a **deprecated alias** for one minor version — `EvalConfig` validation accepts it, logs a `WARNING`-tier deprecation message naming both values and the doc section to update (per `operator-experience.md` Copy Guidelines), and internally normalizes to `"external"`. This avoids a flag-day break for any Builder currently using the stubbed (non-functional) path, while making the rename's existence loudly visible. A hard cutover can follow in a subsequent release once the alias has been observed to be unused (greppable via the deprecation warning's log signal).
- **Rollback**: because the alias path normalizes internally, rolling back this initiative simply means the alias stops being recognized — no data migration, since no persisted artifact stores `test_subject_type` outside `eval_config.json` (which is Builder-owned, version-controlled config).
- **Ordering constraint**: the `TestSubject`/`EvalConfig` model changes (this section) must land *before* `scenario_processor.py` routing changes (ADR-1) can be implemented against them — see Implementation Sequence.

---

## API & Interface Design

### New / Completed Behavior — `external` Test Subject Execution

```
test_subject_type: "external", protocol: "http"
Request:  POST {endpoint} — body: ExternalTaskRequest (scenario fields, custom config,
          rendered prompt content, trace_id), header: {trace_header_name}: {trace_id}
Response: 2xx body: ExternalResponseEnvelope (status/result/metadata/issue/trace_id)
Errors:   non-2xx / unreachable / timeout / malformed body => ExternalOutcome.PROCESS_FAILURE
          2xx with status:"error" or issue present        => ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE

test_subject_type: "external", protocol: "script"
Request:  launch {command} with cwd=<tmpdir>; write <tmpdir>/{request_filename}
          containing ExternalTaskRequest (same fields as above, plus echoed trace_id)
Response: read <tmpdir>/{response_filename} after process exit, parsed as
          ExternalResponseEnvelope
Errors:   non-zero exit / timeout / missing or unparseable response document
                                                          => ExternalOutcome.PROCESS_FAILURE
          exit 0, valid envelope with status:"error" or issue
                                                          => ExternalOutcome.PROCESS_SUCCESS_WITH_ISSUE
```

### Interface Contracts

```python
# processors/script_processor.py — mirrors ExternalHttpProcessor's shape exactly

class ScriptInputProcessor(InputProcessor):
    def __init__(self, config: ProcessorConfig, **kwargs: Any) -> None:
        super().__init__(config)
        self.tracer = get_tracer(__name__)

    async def process(self, inputs: List[ScriptSystemInput]) -> ProcessorResult:
        """For each input: create temp dir, write request doc, launch subprocess,
        await completion (respecting timeout), read + validate response doc,
        classify outcome (ADR-3), return ProcessorResult. Temp dir is guaranteed
        removed on every exit path via `async with tempfile.TemporaryDirectory()`.
        """
        ...
```

```python
# scaffolds/base.py — the "implement one method" contract (FR-8.3)

class _BaseSystemUnderTest(ABC):
    """Shared validation/telemetry/response-assembly. Subclasses implement only `handle`."""

    @abstractmethod
    def handle(self, request: "ExternalTaskRequest | ExternalJudgeRequest") -> "TaskResult | JudgeResult":
        """Do the work. Return value is assembled into a schema-conformant
        ExternalResponseEnvelope by the base class — raise to signal a process
        failure, return a result carrying an `issue` to signal a flagged-but-completed outcome."""
        ...

    # Provided by the base class — not overridden by subclasses:
    #   _parse_and_validate(raw) -> ExternalTaskRequest | ExternalJudgeRequest
    #   _emit_span(name, trace_id, **attrs) -> contextmanager
    #   _assemble_response(result_or_issue) -> ExternalResponseEnvelope
```

### Backward Compatibility

- `local`/in-process execution: zero interface changes; `PromptInputProcessor` and the existing routing branch are untouched (ADR-1).
- `external`/`http` (currently stubbed/non-functional): becomes functional. Any Builder who has *already* configured `"in-situ"`/`"http"` (and is therefore currently getting silent zero-record runs) starts getting real results — a behavior change, but one that fixes a bug rather than breaking working behavior. The deprecation-alias migration path (Schema/Migration Notes) ensures their config keeps validating during the transition.
- Reporters/schema validators: `metadata["trace_id"]` and `JudgedRecord.metadata` are additive `Dict`/`Optional`-defaulted fields — existing `extra="ignore"` consumers and Jinja2 reporter templates that don't reference these keys are unaffected.

---

## Implementation Patterns & Conventions

### Naming Conventions

| Construct | Convention | Example |
|-----------|-----------|---------|
| New processor class | `{Transport}InputProcessor`/`External{Transport}Processor`, matches `ExternalHttpProcessor` (post-rename, ADR-8) | `ScriptInputProcessor`, `ExternalHttpProcessor` |
| New input model | `{Transport}SystemInput`, matches `RemoteSystemInput` | `ScriptSystemInput` |
| Scaffold base classes | `{Transport}SystemUnderTest` | `RemoteSystemUnderTest`, `ScriptSystemUnderTest` |
| Outcome/tier helpers | `classify_external_outcome`, `ExternalOutcome`, mirroring `classify`/`classify_message`/`Tier` naming | — |
| Schema doc | `schema-external-runner.md`, matches `schema-configs.md`/`schema-outputs.md` | — |
| Config flags | `abort_on_{noun}`, snake_case, matches `error_policy.exit_on_error`/`exit_on_warning` | `abort_on_exec_failure` |

### Error Handling Pattern

```python
# Both new/modified processors classify *before* raising — they never raise
# ProcessorError for an outcome that should be a recoverable WARNING. The
# classification result rides in ProcessorResult.metadata["external_outcome"]
# and ProcessorResult.error (string), and _spool_result's existing
# classify_message(result.error) / error_policy.should_halt(tier) path
# (scenario_processor.py:290-296) does the actual halting — unchanged.
```

**Rules:**
- Never call `raise RunPolicyError(...)` from inside a processor — that is `Step.safe_execute`'s/`_spool_result`'s job, per existing convention. Processors classify and report; steps halt.
- All externally-sourced strings (HTTP response bodies, subprocess stderr, response-document content) that land in `ProcessorResult.error`/`metadata` must be bounded in length before storage (existing convention implied by "Never print stack traces to the terminal" — applies equally to not dumping unbounded external payloads into `run.log`/records).
- Confinement checks (ADR-5) raise `ProcessorError` with a message naming the offending path and the expected boundary — mirrors `_load_markdown_judge_config`'s `ConfigError` message style ("X resolves outside Y - Path traversal not allowed").

### Testing Pattern

```python
# tests/unit/processors/test_script_processor.py
@pytest.mark.unit
async def test_script_processor_round_trip(tmp_path):
    """Real tempfile dirs, a real trivial echo-script subprocess, no MagicMock
    of filesystem or process — per [[feedback_real_tests]]."""
    ...

# tests/integration/test_external_runner_e2e.py
@pytest.mark.integration
async def test_external_http_path_produces_records(httpx_mock_server):
    """Real ScenarioProcessorStep + real ExternalHttpProcessor against a
    local test-double HTTP server (not a mocked client) — mirrors
    test_oneshot_pipeline_e2e.py's approach."""
    ...
```

**Coverage expectations:** 100% on `classify_external_outcome` (small, pure, exhaustively enumerable — 8 cases); round-trip integration coverage for both transports (the PRD's explicit Measurable Outcome); scaffold base classes get a dedicated round-trip test that drives a minimal subclass through `_parse_and_validate` → `handle` → `_assemble_response` against real (Gavel-generated) request fixtures.
**Mocking strategy:** Mock at the *transport boundary* — a local test-double HTTP server (e.g. `pytest-httpserver` or a minimal `asyncio` server fixture) for the http path, a real trivial subprocess (a checked-in fixture script) for the script path. Do not mock `httpx`/`asyncio.create_subprocess_exec` themselves — that would test the mocks, not the integration, per [[feedback_real_tests]].

---

## Security & Performance

### Security

| Concern | Mitigation |
|---------|-----------|
| Shell injection via configured script command | `ScriptSystemInput.command: List[str]`, invoked via `asyncio.create_subprocess_exec(*command)` — no shell, no string interpolation (ADR-4/Tech Stack) |
| Path traversal via configured request/response filenames | Directory is fixed to the per-invocation temp dir; only filenames are configurable; runtime confinement check reuses `judge_runner.py`'s reviewed `resolved.startswith(...)` pattern (ADR-5) |
| Secrets in HTTP auth config (`bearer_token`/`api_key`/`username`+`password`) | Reuses `ExternalHttpProcessor._build_request_kwargs`'s existing handling unchanged (method carried over verbatim through the rename, ADR-8); documented schemas (FR-6) mark these fields explicitly as secret-bearing so external-system implementers (via the scaffold) know not to log them verbatim |
| Unbounded external payload sizes (HTTP response bodies, subprocess stdout/stderr/response documents) | Bound and truncate before storing in `ProcessorResult`/`OutputRecord`/`run.log`; document the limit in `schema-external-runner.md` so external-system authors know what's preserved |
| Temp-directory collision under concurrency (`async_config.num_workers > 1`) | `tempfile.TemporaryDirectory()` generates a unique directory per invocation by construction — no shared-state coordination needed (FR-3.2) |

### Performance

| Concern | Target | Approach |
|---------|--------|---------|
| Concurrency parity with `local`/`http` paths | No serialization introduced; respects `async_config.num_workers` | `ScriptInputProcessor.process()` is `async`, driven by the same `Executor`/`asyncio` concurrency the other processors use; temp-dir creation is a fast syscall, not a bottleneck at expected worker counts |
| Subprocess launch overhead | Bounded by `async_config.task_timeout_seconds` | `asyncio.wait_for` enforces the existing timeout config; no new timeout knob unless the Open Question resolves to "needs independent script timeout" (currently recommended: reuse the existing one, see ADR-4) |
| Schema-doc generation cost | Negligible, build/doc-time only | `model_json_schema()` runs at doc-generation time (a script invoked during development/CI), not at eval-run time — zero runtime cost |

### Observability

- **Logs:** Per-invocation start/outcome log lines at the same level/verbosity as existing `local`/`http` processor logging, each including `trace_id` and (for script) the command + exit code, (for http) the endpoint + status code — per `operator-experience.md` Copy Guidelines ("always include the correlator").
- **Metrics:** None new — existing `telemetry.jsonl` span/attribute mechanism covers per-invocation timing; no new counter/metric system introduced (consistent with "no parallel observability paths" constraint in `operator-experience.md`).
- **Traces:** Both new/modified processors open a span per invocation via `self.tracer` (matching `ExternalHttpProcessor`'s existing `get_tracer(__name__)` pattern), attaching `trace_id` (from `get_current_run_id()`-scoped context) as a span attribute — outbound as an HTTP header / request-document field, inbound as `metadata["trace_id"]` on the resulting record (ADR-2).

---

## Implementation Sequence

1. **Foundation** *(blocking)* — `models/config.py` (`TestSubject` protocol/flags/config shapes, `EvalConfig` value handling for the rename + alias) and `models/runtime.py` (`ScriptSystemInput`, `ExternalIssue`, `ExternalResponseEnvelope`, `JudgedRecord.metadata`) land first; everything else is built against these types. Includes the `classify_external_outcome`/`ExternalOutcome`/`Tier`-mapping helper (ADR-3), since both processors depend on it. **Also includes correcting `gavel-skill`'s `references/config-schema.md`** (ADR-9) — done by the same engineer, immediately after the `TestSubject`/`protocol` shape stabilizes, while the mapping is freshest; this is a blocking precondition for the skill to meaningfully assist with *any* part of this initiative, not a trailing doc task. **Foundation now also includes** (per ADR-10, the reserved forward-compat seam): (a) adding the optional `adapter: Optional[str] = "gavel"` field to `TestSubject`, and (b) structuring `ExternalHttpProcessor`/`ScriptInputProcessor`/`classify_external_outcome` with the transport/wire-format/classification seam the new ADR describes — i.e. making the shipped code extension-ready for a future front-door adapter, not building that adapter now.
2. **Rename + complete the HTTP path** *(depends on 1)* — the `ClosedBoxInputProcessor` → `ExternalHttpProcessor` rename (ADR-8, mechanical — imports/instantiation/tests/docstrings) lands together with `scenario_processor.py` routing/input-building for `external`/`http` (ADR-1) and `ExternalHttpProcessor` modifications for `trace_id` header injection and `classify_external_outcome` integration, since all three touch the same file/call sites — bundling avoids two separate diffs colliding on the same lines. This is the *highest-value, lowest-risk* slice — it turns an existing silent-failure into working behavior using an already-implemented processor, and validates the foundation types end-to-end before the net-new script path is built on top of them.
3. **Script path** *(depends on 1, informed by 2)* — `ScriptInputProcessor` (temp-dir lifecycle, subprocess launch/await/timeout, request/response document I/O with confinement checks) and its `scenario_processor.py` routing branch. Built second so it can reuse the routing/classification patterns just proven out in step 2.
4. **Judge delegation** *(depends on 2 and 3)* — extend `judge_runner.py`/`JudgeExecutor` to support `external`/`http` and `external`/`script` judge configs through the now-working task-execution transports (FR-7); reuses rather than duplicates the transport implementations.
5. **Documented schemas** *(depends on 1; can run in parallel with 2-4)* — `model_json_schema()` export script + `docs/specs/schema-external-runner.md`, generated from the foundation models (`ExternalTaskRequest`/`ExternalJudgeRequest`/`ExternalResponseEnvelope` and friends). Should be drafted early enough to give scaffold implementation (step 6) something concrete to validate against, but the generation mechanism itself only needs the foundation types to exist.
6. **Scaffold base classes + materialization** *(depends on 5)* — `scaffolds/` package (mixin + two base classes + templates + `_materialize.py` + eval-creation hook). Deliberately sequenced last among the build steps: the scaffolds *are* the documented schemas made concrete on the other side of the wire, so they should be written against finalized schemas, not evolving ones.
7. **Skill flow extension** *(depends on 2 and 3 — needs a working feature to document accurately)* — extend `SKILL.md` §2 (setup flow) and §6 (debug flow) to walk a Builder through `external`/`http`|`script` configuration and two-tier-failure interpretation (ADR-9, second half), in the vocabulary `operator-experience.md` defines. Sequenced after the underlying paths work, so the skill's guidance describes real, testable behavior rather than a moving target — unlike `references/config-schema.md`'s correction (step 1), which only needed the *shape* to stabilize, this needs the *behavior* to exist.
8. **Testing** *(parallel with 2-7, per slice)* — unit tests for `classify_external_outcome` and `ScriptInputProcessor` land alongside their implementations; integration/e2e round-trip tests (both transports, both task and judge, scaffold round-trip) land as each dependency becomes available; the "no regressions on `local`" gate runs continuously from step 1 onward.

**Parallel work opportunities:** Steps 2 and 3 *could* technically proceed in parallel once step 1 lands (they touch disjoint processor files and disjoint `scenario_processor.py` branches) — but sequencing them (2 then 3) is recommended so the script path can borrow proven patterns rather than two engineers independently discovering the same `classify_external_outcome`/routing idioms. Step 5 (schemas) can start as soon as step 1's foundation types stabilize, in parallel with steps 2-4. Step 7 (skill flows) can start as soon as step 2 (HTTP) is functional, running in parallel with step 3 (script) — its script-path coverage simply lands a little later.

**Known implementation risks:**
- **Risk: completing the HTTP stub surfaces deeper variant/model-semantics gaps** (already flagged in `prd.md` Risk Mitigation) — explore as a short spike at the *start* of step 2, before committing further implementation time; if gaps are large, narrow the MVP slice and document follow-ups rather than expanding scope mid-stream.
- **Risk: subprocess timeout-then-kill semantics differ subtly across platforms** (SIGTERM/SIGKILL behavior, process-group vs. single-process termination for scripts that spawn children) — worth a small spike during step 3 to confirm the chosen approach behaves consistently in the project's target environments before relying on it for classification correctness.
