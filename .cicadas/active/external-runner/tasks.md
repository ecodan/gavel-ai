
---
summary: "Two partitions complete: Foundation (ids 1-15) and HTTP completion+rename (ids 16-27). Active: feat/external-http-rename fully merged into initiative branch. Next in DAG: feat/external-runner-schemas and feat/external-script-processor (both now unblocked, parallel-capable). Judge delegation, scaffolds, and skill-flows follow after both transports merge."
phase: "tasks"
when_to_load:
  - "When selecting the next implementation task or reviewing completion state."
  - "When checking partition progress, PR boundaries, or execution sequencing."
depends_on:
  - "prd.md"
  - "operator-experience.md"
  - "tech-design.md"
  - "approach.md"
modules:
  - "src/gavel_ai/models/config.py"
  - "src/gavel_ai/models/runtime.py"
  - "src/gavel_ai/core/issue_classifier.py"
  - "src/gavel_ai/core/steps/scenario_processor.py"
  - "src/gavel_ai/core/steps/judge_runner.py"
  - "src/gavel_ai/processors/external_http_processor.py"
  - "src/gavel_ai/processors/script_processor.py"
  - "src/gavel_ai/scaffolds/"
  - "docs/specs/schema-external-runner.md"
  - "src/gavel_ai/skill/gavel-skill/"
index:
  partition_foundation: "## Partition: feat/external-runner-foundation"
  partition_http_rename: "## Partition: feat/external-http-rename"
  partition_schemas: "## Partition: feat/external-runner-schemas"
  partition_script_processor: "## Partition: feat/external-script-processor"
  partition_judge_delegation: "## Partition: feat/external-judge-delegation"
  partition_scaffolds: "## Partition: feat/external-runner-scaffolds"
  partition_skill_flows: "## Partition: feat/external-runner-skill-flows"
  initiative_boundary: "## Initiative Boundary"
next_section: "## Partition: feat/external-script-processor"
---

# Tasks: external-runner

<!-- Partitions appear in approach.md order. Sections map to feature branches per the Partitions DAG. -->

## Partition: feat/external-runner-foundation

- [x] `models/config.py`: add `protocol: Literal["http", "script"]` to `TestSubject` (active when `test_subject_type == "external"`), with protocol-specific `config` sub-shape validation; constructing with `protocol="bogus"` raises `pydantic.ValidationError` naming `protocol` and the allowed values <!-- id: 1 -->
- [x] `models/config.py`: add `abort_on_exec_failure: bool = True` and `abort_on_process_error: bool = False` to `TestSubject`, defaulting correctly when unset and accepting explicit overrides of both <!-- id: 2 -->
- [x] `models/config.py`: add `adapter: Optional[str] = "gavel"` to `TestSubject` per ADR-10 — additive/optional, defaults preserve current `external`/`http`|`script` behavior exactly; omitting it or passing `adapter="gavel"` are equivalent, and no other value is implemented/accepted as meaningful in this MVP <!-- id: 3 -->
- [x] `models/config.py`: extend `EvalConfig.test_subject_type` to accept `"external"` and treat `"in-situ"` as a deprecated alias that validates, normalizes internally to `"external"`, and emits exactly one `WARNING`-tier log record naming both `"in-situ"` and `"external"` <!-- id: 4 -->
- [x] `models/runtime.py`: add `ScriptSystemInput` (with `command: List[str]`, rejecting a bare `str`; `request_filename`/`response_filename` defaulting to `request.json`/`response.json`), `ExternalIssue`, and `ExternalResponseEnvelope` (validating `status="ok"`/`status="error"` shapes and rejecting `status="bogus"` with `ValidationError`) <!-- id: 5 -->
- [x] `models/runtime.py`: add `metadata: Dict[str, Any] = Field(default_factory=dict)` to `JudgedRecord` — additive, defaults to `{}`, and round-trips through `model_dump()`/JSON for an existing `extra="ignore"` consumer fixture <!-- id: 6 -->
- [x] `core/issue_classifier.py` (or sibling module per ADR-3): add `ExternalOutcome` enum and `classify_external_outcome(outcome, abort_on_exec_failure, abort_on_process_error) -> Tier` pure mapping function, structured per ADR-10 as adapter-parameterizable (a strategy/mapping shape keyed by `adapter`, with the Gavel mapping registered as the sole implementation today — a structuring convention on code already being written, not extra scope), placed beside `classify`/`classify_message` <!-- id: 7 -->
- [x] `tests/unit/models`: write parametrized unit tests covering `TestSubject`/`EvalConfig` validation (valid/invalid `protocol`, `abort_on_*` defaults and overrides, `adapter` default/override equivalence), the `"in-situ"`→`"external"` alias normalization with an assertion on the emitted `WARNING` log record, and `ScriptSystemInput`/`ExternalResponseEnvelope`/`JudgedRecord.metadata` construction and round-trip behavior <!-- id: 8 -->
- [x] `tests/unit/core`: write a parametrized unit test covering all 8 flag/outcome combinations for `classify_external_outcome` (e.g. `PROCESS_FAILURE` × `abort_on_exec_failure` ∈ {True, False}, `PROCESS_SUCCESS_WITH_ISSUE` × `abort_on_process_error` ∈ {True, False}, plus `None` → `Tier.OK`), achieving 100% coverage of the function per `tech-design.md`'s Testing Pattern coverage expectations <!-- id: 9 -->
- [x] `src/gavel_ai/skill/gavel-skill/references/config-schema.md`: replace the stale `"local" | "remote"` / `"acp" | "open_ai"` documentation with the real `"local" | "external"` / free-text `protocol` shape and the new `protocol`/`abort_on_*`/`adapter` sub-shapes and flags this partition defines (ADR-9, first half); spot-check `SKILL.md` §0/§2 to ensure no other doc in the skill package contradicts the corrected shape <!-- id: 10 -->
- [x] Verify `config-schema.md` no longer contains the strings `"remote"` or `"acp"`/`"open_ai"` as documented `test_subject_type`/`protocol` values (`grep -n 'remote\|acp\|open_ai' src/gavel_ai/skill/gavel-skill/references/config-schema.md` returns no matches against documented values) <!-- id: 11 -->
- [x] Run `uv run pytest tests/unit/models -m unit` and `uv run pytest tests/unit/core -m unit` (or the relevant module paths for the new tests) and confirm both exit 0 <!-- id: 12 -->
- [x] Run `uv run mypy src/gavel_ai/models/config.py src/gavel_ai/models/runtime.py src/gavel_ai/core/issue_classifier.py` and confirm it exits 0 with no new errors <!-- id: 13 -->
- [x] Run `uv run pytest -m unit`, `uv run mypy src/`, and `uv run ruff check src/` across the full tree and resolve any findings introduced by this partition before merge <!-- id: 14 -->
- [x] Confirm Foundation's full Acceptance Criteria checklist (approach.md Partition 1) is green end-to-end — this is the sole DAG root; no downstream partition may start until this task is complete <!-- id: 15 -->

## Partition: feat/external-http-rename

- [x] Run the rename audit: `grep -rl "closedbox\|closed.box\|closed_box\|ClosedBox" src/ tests/ docs/` and record the full list of ~14 files to update (including `processors/__init__.py`, `core/steps/report_runner.py`, docstring references in `models/config.py`/`models/runtime.py`, and `docs/.private/` notes) <!-- id: 16 -->
- [x] Rename `processors/closedbox_processor.py` → `processors/external_http_processor.py` and `ClosedBoxInputProcessor` → `ExternalHttpProcessor` (ADR-8); update every import/instantiation/docstring reference identified by the audit so `from gavel_ai.processors.external_http_processor import ExternalHttpProcessor` succeeds and `from gavel_ai.processors.closedbox_processor import ClosedBoxInputProcessor` raises `ModuleNotFoundError` <!-- id: 17 -->
- [x] Rename `tests/unit/processors/test_closedbox_processor.py` → `tests/unit/processors/test_external_http_processor.py` and update its contents to reference `ExternalHttpProcessor`; confirm `grep -rl "closedbox\|closed.box\|closed_box\|ClosedBox" src/ tests/ docs/` returns zero matches <!-- id: 18 -->
- [x] Within `external_http_processor.py`, factor "send/receive over the wire" apart from "build the outbound payload" and "parse the inbound response" per ADR-10's transport/wire-format/classification seam (a structuring convention on code already being written here, not new scope) <!-- id: 19 -->
- [x] `core/steps/scenario_processor.py`: extend the routing branch (around `:247-249`) and input-building block (around `:175-214`/`:306`) with a parallel branch for `test_subject_type == "external" and protocol == "http"` that builds one `RemoteSystemInput` per scenario/variant from `system_id`/`protocol`/`config` and routes it to `ExternalHttpProcessor`, closing the `inputs == []` stub — verified by an integration test asserting `len(inputs) == expected_count` <!-- id: 20 -->
- [x] `external_http_processor.py`: add `trace_id` HTTP-header injection on outbound requests (configurable header name, documented default, equal to `get_current_run_id()`'s trace value) and populate `metadata["trace_id"]` in `_make_output_record` for externally-executed records <!-- id: 21 -->
- [x] `docs/specs/schema-outputs.md`: document the `metadata["trace_id"]` key as present (and resolvable to a `telemetry.jsonl` span for the same `run_id`) on externally-executed `OutputRecord`/`JudgedRecord` entries, and absent on in-process records, per FR-4.3 and ADR-2's "Affects" list <!-- id: 22 -->
- [x] `external_http_processor.py`: wire `classify_external_outcome` into the response-handling path — derive `ExternalOutcome` from HTTP status / `ExternalResponseEnvelope.status`/`issue`, call the mapping function with the `TestSubject`'s abort flags, and surface the resulting tier through `ProcessorResult.error`/`metadata["external_outcome"]` so `_spool_result`'s existing `classify_message`/`should_halt` path handles it without re-deriving the tier (per ADR-3 and the Error Handling Pattern in tech-design.md) <!-- id: 23 -->
- [x] `tests/unit/processors/test_external_http_processor.py`: write/extend unit tests against a local test-double HTTP server covering both outcome tiers (`process_failure`, `process_success_with_issue`) and both abort-flag settings, plus the `trace_id` header-injection and `metadata["trace_id"]` population behaviors <!-- id: 24 -->
- [x] `tests/integration/test_processor_chain_e2e.py`: write/extend an end-to-end integration test driving `ScenarioProcessorStep` with `test_subject_type: "external"`/`protocol: "http"` against a local test-double server — asserting a 2xx `ExternalResponseEnvelope(status="ok", ...)` produces a populated `results_raw.jsonl` record with matching `metadata["trace_id"]` and `timing_ms`; a 503 produces a `process_failure`-classified record and (default `abort_on_exec_failure=True`) halts the run via `RunPolicyError`; and a `200`-with-warning-`issue` envelope produces a `WARNING`-tier log entry, continues the run, and carries the issue in `metadata`/`error` <!-- id: 25 -->
- [x] Run the existing `local`/`PromptInputProcessor` regression test (`tests/integration/test_oneshot_pipeline_e2e.py` or equivalent) and confirm it passes unchanged — zero behavior change to the `local` path (explicit Quality Gate) <!-- id: 26 -->
- [x] Run `uv run pytest tests/integration/test_processor_chain_e2e.py -m integration`, `uv run pytest -m unit`, and `uv run mypy src/gavel_ai/processors/external_http_processor.py src/gavel_ai/core/steps/scenario_processor.py`, and confirm all exit 0 with no new mypy errors <!-- id: 27 -->

## Partition: feat/external-script-processor

- [x] `processors/script_processor.py` (new): scaffold `ScriptInputProcessor(InputProcessor)` conforming to the `Processor`/`ProcessorConfig` constructor pattern (`config: ProcessorConfig, **kwargs`), with `self.tracer = get_tracer(__name__)` matching `ExternalHttpProcessor`'s convention; export it from `processors/__init__.py` so `from gavel_ai.processors.script_processor import ScriptInputProcessor` and `from gavel_ai.processors import ScriptInputProcessor` both succeed <!-- id: 28 -->
- [x] Implement the per-invocation lifecycle in `ScriptInputProcessor`: `with tempfile.TemporaryDirectory()`, write the JSON request document (scenario fields, custom config, `trace_id`), launch via `asyncio.create_subprocess_exec(*command, cwd=tmpdir)` (argument-list form, no shell, per ADR-4/Tech Stack), and await completion under `async_config.task_timeout_seconds` via `asyncio.wait_for(...)` with SIGTERM→SIGKILL escalation on timeout, capturing bounded stdout/stderr <!-- id: 29 -->
- [x] Implement response-document read + path-confinement check in `ScriptInputProcessor`, reusing/adapting `judge_runner.py::_load_markdown_judge_config`'s `resolved.startswith(...)` pattern (ADR-5) and `ExternalResponseEnvelope` validation; a `TestSubject.config` attempting a response path containing `../` is rejected with a `ProcessorError` naming the offending path and expected boundary <!-- id: 30 -->
- [x] Wire `classify_external_outcome` into `ScriptInputProcessor`'s outcome-handling path identically to Partition 2's HTTP integration — derive `ExternalOutcome` from exit code / response-document presence / envelope `status`/`issue`, and structure the request-building/response-parsing apart from the temp-dir/subprocess transport mechanics per ADR-10 <!-- id: 31 -->
- [x] `core/steps/scenario_processor.py`: extend routing/input-building with the `test_subject_type == "external" and protocol == "script"` branch, building one `ScriptSystemInput` per scenario/variant and routing it to `ScriptInputProcessor` <!-- id: 32 -->
- [x] Add checked-in fixture scripts under `tests/fixtures/scripts/` covering: success, non-zero exit, timeout, missing `response.json`, and a warning-`issue` response <!-- id: 33 -->
- [x] `tests/unit/processors/test_script_processor.py`: write a real-`tmp_path`, real-fixture-subprocess round-trip test (no `MagicMock` of filesystem/process) asserting a populated `ProcessorResult` (`result`, `timing_ms`, `metadata`) and that the temp directory no longer exists on disk after `process()` returns; assert the written request document is valid JSON with `trace_id` present <!-- id: 34 -->
- [x] `tests/unit/processors/test_script_processor.py`: write tests for the non-zero-exit fixture (classified `PROCESS_FAILURE`, bounded `stderr` in `metadata["stderr"]`), the timeout fixture (process terminated, classified `PROCESS_FAILURE`, temp dir still cleaned up), and the missing-`response.json` fixture (classified `PROCESS_FAILURE` with a message naming the missing path) <!-- id: 35 -->
- [x] `tests/unit/processors/test_script_processor.py`: write a test for the warning-`issue` fixture (`{"status": "ok", "issue": {"code": "low_confidence", "level": "warning", ...}}` produces `WARNING`-tier classification, continues the run under default `abort_on_process_error=False`, and the issue lands in `metadata`/`error`) and a concurrency test asserting concurrent invocations never collide on temp-directory paths <!-- id: 36 -->
- [x] `tests/integration/test_external_runner_e2e.py` (new): write an end-to-end `ScenarioProcessorStep` integration test for `test_subject_type: "external"`/`protocol: "script"` asserting `results_raw.jsonl` records match the same schema shape (`timing_ms`, `error`, `metadata`, `timestamp`) as `local`/in-process records <!-- id: 37 -->
- [x] Run `uv run pytest tests/unit/processors/test_script_processor.py -m unit` and confirm it exits 0 <!-- id: 38 -->
- [x] Run `uv run pytest tests/integration/test_external_runner_e2e.py -m integration -k script` and confirm it exits 0 <!-- id: 39 -->
- [x] Run `uv run mypy src/gavel_ai/processors/script_processor.py` and confirm it exits 0 with no new errors <!-- id: 40 -->

## Partition: feat/external-judge-delegation

- [x] `models/config.py`: extend the judge config model to accept `protocol`/`config`/`system_id`/abort-flag fields consistent with `TestSubject`'s shape, enabling judges to delegate scoring via `http`/`script` transports (FR-7.1) <!-- id: 41 -->
- [x] `core/steps/judge_runner.py`: extend `JudgeRunnerStep`/`JudgeExecutor` to route external-judge configs through the now-functional `ExternalHttpProcessor`/`ScriptInputProcessor` (constructing `RemoteSystemInput`/`ScriptSystemInput` from judge-specific request content — rendered judge criteria/prompt instead of task prompts) rather than duplicating transport logic <!-- id: 42 -->
- [x] `core/steps/judge_runner.py`: map processor results into `JudgedRecord`s (`judge_id`, `score`, `reasoning`, `error`, `timestamp`, `metadata["trace_id"]`), routing classification through `classify_external_outcome`/the existing `IssueClassifier`/`ErrorPolicy` so output is indistinguishable in shape from in-process LLM-judge output <!-- id: 43 -->
- [x] `tests/unit/core/test_judge_runner.py`: write unit tests for the extended judge config validation (both transports, `protocol`/`config`/`system_id`/abort-flag fields) and a parametrized tier-classification matrix mirroring Partition 2/3's process-failure / process-success-with-issue cases, including respecting `abort_on_exec_failure`/`abort_on_process_error` <!-- id: 44 -->
- [x] `tests/integration/test_external_runner_e2e.py`: write an integration round-trip test asserting (b) a `protocol: "script"` judge against a fixture judge-script produces a `JudgedRecord` of identical shape via the same temp-dir handoff, and (c) externally-delegated `JudgedRecord`s flow with no schema-shape difference from in-process judge output (diffed-fields assertion against an in-process fixture); note: HTTP judge test uses fixture-level mock rather than a live server <!-- id: 45 -->
- [x] Run `uv run pytest tests/unit/core/test_judge_runner.py -m unit` and `uv run pytest tests/integration/test_external_runner_e2e.py -m integration -k judge` and confirm both exit 0 <!-- id: 46 -->
- [x] Run `uv run mypy src/gavel_ai/core/steps/judge_runner.py` and confirm it exits 0 with no new errors <!-- id: 47 -->

## Partition: feat/external-runner-schemas

- [x] Finalize the `ExternalTaskRequest`/`ExternalJudgeRequest` Pydantic models (the PRD specifies minimum content per FR-6.2/FR-6.3, not final shape), placed alongside the already-foundation-landed `ExternalResponseEnvelope`/`ExternalIssue` <!-- id: 48 -->
- [x] Write the schema-generation script (e.g. `scripts/generate_external_schemas.py`, co-located per existing doc-generation conventions — exact path TBD at implementation time) that calls `model_json_schema()` on each of the eight request/response models (HTTP task request/response, HTTP judge request/response, script task request/response, script judge request/response) and writes results to static JSON files or embeds them in the markdown doc <!-- id: 49 -->
- [x] `docs/specs/schema-external-runner.md` (new): author prose descriptions of all eight documented payload shapes, with links to/embeds of the generated schemas and a documented limit/truncation note for unbounded payload fields per the Security & Performance "bound and truncate" guidance; verify each request schema's `properties` includes scenario data, custom config, required prompt/judge content, and `trace_id` (FR-6.2), and each response schema's `properties` includes `status`, `result`, `metadata`, and an `issue` envelope distinguishing the two error tiers (FR-6.3) <!-- id: 50 -->
- [x] Cross-link `docs/specs/schema-external-runner.md` from (or alongside) `docs/specs/schema-configs.md`/`schema-outputs.md` per the existing doc-organization convention <!-- id: 51 -->
- [x] Write a test asserting the generation script produces valid JSON Schema for all eight shapes (`jsonschema.Draft202012Validator.check_schema(schema)` does not raise for each) <!-- id: 52 -->
- [x] Write a round-trip check test: a real Gavel-generated request payload (sourced from a Partition 2/3 integration-test fixture) validates successfully against its corresponding published schema <!-- NEEDS MANUAL REVIEW: depends on fixtures existing from Partitions 2-4; verify cross-partition fixture reuse path at implementation time --> <!-- id: 53 -->
- [x] Run `uv run python scripts/generate_external_schemas.py` (or the chosen invocation) and confirm `docs/specs/schema-external-runner.md` exists, documents exactly eight payload shapes, and the schema-validity and round-trip tests both pass <!-- id: 54 -->

## Partition: feat/external-runner-scaffolds

- [ ] `scaffolds/base.py` (new package `scaffolds/`: `__init__.py`, `base.py`, `remote.py`, `script.py`, `_materialize.py`, `templates/`): implement the `_BaseSystemUnderTest` mixin (ADR-6) with `_parse_and_validate`, `_emit_span`, `_assemble_response`, built against the Partition 5 finalized schemas/models, providing `trace_id`-correlated log/span emission (mirroring, not importing, `telemetry/spans.py` conventions) and `status`/`issue` envelope assembly so subclasses implement only `handle(request) -> result` (FR-8.3) <!-- id: 55 -->
- [ ] `scaffolds/remote.py` and `scaffolds/script.py`: implement `RemoteSystemUnderTest` (HTTP server entrypoint glue) and `ScriptSystemUnderTest` (script `main()` glue reading/writing temp-dir documents), each adding only transport glue atop the `_BaseSystemUnderTest` mixin; verify importing either does not pull in any `gavel_ai.core.*` pipeline/runtime module (assert via `sys.modules` delta inspection in a test) <!-- id: 56 -->
- [ ] `scaffolds/templates/`: author one scaffold template file per protocol (`http`, `script`), each a thin subclass stub with inline comments pointing at the documented schema (`schema-external-runner.md`) and the canonical base class <!-- id: 57 -->
- [ ] `scaffolds/_materialize.py`: implement `_materialize(eval_dir, protocol="http"|"script")` — copies the protocol-appropriate template into `{eval_dir}/scripts/{name}_scaffold.py` with a header comment recording the source module path and a content-hash/version marker (ADR-7 drift-detection mitigation); the resulting file must be syntactically valid Python (`ast.parse` does not raise) <!-- id: 58 -->
- [ ] Wire `_materialize` into the existing eval-creation/`gavel init` scaffolding path with one new conditional call, invoked only when `test_subject_type == "external"`; creating a new `external` eval produces a scaffold file in that eval's `scripts/` directory while a `local`-only eval does not <!-- id: 59 -->
- [ ] `pyproject.toml`: extend `[tool.setuptools.package-data]` to include `scaffolds/templates/*`, alongside the existing `gavel_ai = ["reporters/templates/*"]` entry, so installed packages ship the templates <!-- NEEDS MANUAL REVIEW: exact packaging verification command depends on build/install method used in CI --> <!-- id: 60 -->
- [ ] `tests/unit/scaffolds/`: write round-trip tests driving a minimal subclass overriding only `handle(request) -> result` through `_parse_and_validate` → `handle` → `_assemble_response` against real Gavel-generated request fixtures (from Partition 2/3), for both `RemoteSystemUnderTest` and `ScriptSystemUnderTest`; assert malformed-request rejection produces a clear error naming the missing/mismatched field and the `schema-external-runner.md` path (not a generic stack trace); assert `handle` raising → `status: "error"` and `handle` returning an issue-bearing result → `status: "ok"` with `issue` populated, both schema-valid; assert a structured log line and (when OTEL is configured) a span carrying `trace_id` is emitted per `handle` invocation <!-- id: 61 -->
- [ ] Write a materialization integration test: run the eval-creation CLI path (e.g. `uv run gavel init` against a temp eval directory configured `test_subject_type: "external"`) and assert the scaffold file is present, header comment and version marker exist, and the file parses as valid Python; assert a `local`-only eval produces no scaffold file <!-- id: 62 -->
- [ ] Run `uv run pytest tests/unit/scaffolds -m unit`, the materialization integration test, and `uv run mypy src/gavel_ai/scaffolds/`, and confirm all exit 0 with no new mypy errors <!-- id: 63 -->

## Partition: feat/external-runner-skill-flows

- [x] Read `operator-experience.md`'s Operator Flows (Flow 1, Flow 2) and Copy and Message Guidelines in full; extract the exact phrasing patterns (tier vocabulary, "always include the correlator") the skill must relay verbatim <!-- id: 64 -->
- [x] `SKILL.md` §2 (setup flow): extend with a documented conversational path for `test_subject_type: "external"` covering both `protocol: "http"` (endpoint/auth config) and `protocol: "script"` (command/args/timeout config), including how `abort_on_exec_failure`/`abort_on_process_error` are explained in operator vocabulary (e.g. "should the run stop if the service is unreachable?") <!-- id: 65 -->
- [x] `SKILL.md` §6 (debug flow): extend with the two-tier-failure debugging flow — how to read the Rich panel/`run.log`, distinguish and relay "process failure" vs. "process success with internal error/warning" by naming the tier, the cause, and `trace_id`, matching `operator-experience.md`'s Copy and Message Guidelines (not softening "process failure" into vaguer phrasing) <!-- id: 66 -->
- [x] `references/cli-reference.md`: update to document any `external`-specific CLI output/flags introduced by Partitions 2-4, or explicitly note that none were needed (since execution still goes through `gavel oneshot run`) <!-- NEEDS MANUAL REVIEW: "explicitly notes none were needed" requires a human judgment call on completeness --> <!-- id: 67 -->
- [x] Verify neither `SKILL.md` nor `references/cli-reference.md` contains the stale strings `"remote"` or `"acp"`/`"open_ai"` as documented `test_subject_type`/`protocol` values — consistency check against Partition 1's `config-schema.md` correction <!-- id: 68 -->
- [x] Produce a walkthrough transcript or fixture conversation (per the skill's test-conversation convention, if one exists) demonstrating the skill correctly explaining at least one process-failure and one process-success-with-issue scenario using the tier vocabulary verbatim <!-- NEEDS MANUAL REVIEW: requires manual/agent-mediated verification of conversational quality, not purely mechanical --> <!-- id: 69 -->
- [x] Run any existing skill self-consistency/update scripts (e.g. `uv run python src/gavel_ai/skill/gavel-skill/scripts/update_cli_reference.py --check`) and confirm no drift warnings <!-- id: 70 -->

## Initiative Boundary

- [ ] Open PR: initiative/external-runner -> master and await merge approval before continuing <!-- id: 71 -->
