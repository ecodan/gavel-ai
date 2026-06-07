---
summary: "Three partitions, sequential. P1 (Foundations): data models, CompositeStep, IterationEvalContext/IterationRunContext, TuningAgent, bundled meta-prompt, unit tests. P2 (Engine): TuneStep, AutotuneIterationStep (4-criteria convergence), AutotuneWorkflow (PrepareStep + resume), AutotuneReporter + HTML template, unit tests, integration test. P3 (Surface): CLI create/run commands, scaffolding, full test suite, gavel-skill autotune section (7 stages), config-schema.md, cli-reference.md regeneration."
phase: "tasks"
when_to_load:
  - "When picking up the next task to implement."
  - "When checking what is complete and what remains."
depends_on:
  - "approach.md"
  - "tech-design.md"
modules:
  - "src/gavel_ai/models/config.py"
  - "src/gavel_ai/core/steps/base.py"
  - "src/gavel_ai/core/contexts.py"
  - "src/gavel_ai/core/autotune/tuning_agent.py"
  - "src/gavel_ai/core/steps/tune_step.py"
  - "src/gavel_ai/core/steps/autotune_iteration_step.py"
  - "src/gavel_ai/core/workflows/autotune.py"
  - "src/gavel_ai/reporters/autotune_reporter.py"
  - "src/gavel_ai/cli/commands/autotune.py"
  - "src/gavel_ai/skill/gavel-skill/SKILL.md"
index:
  p1: "## Partition 1: Foundations"
  p2: "## Partition 2: Engine"
  p3: "## Partition 3: Surface"
next_section: null
---

# Tasks: feat-autotune

---

## Partition 1: Foundations → `feat/autotune-foundations`

- [ ] **Data models** — Add `TuningConfig`, `IterationMetadata`, `AutotuneRunSummary` to `models/config.py`; extend `EvalConfig.workflow_type` to include `"autotune"`; add `EvalConfig.tuning: Optional[TuningConfig] = None` <!-- id: 100 -->
- [ ] **Step base** — Add `StepPhase.AUTOTUNE_ITERATION` and `StepPhase.TUNING` enum values; add `CompositeStep(Step)` base class with `child_steps` list and `run_children(context, error_policy) -> bool` to `core/steps/base.py` <!-- id: 101 -->
- [ ] **Contexts** — Add `IterationEvalContext` (wraps `LocalFileSystemEvalContext`, overrides `get_prompt()` to read vN from `prompts.toml`) and `IterationRunContext` dataclass to `core/contexts.py`; also add `skip_snapshot: bool = False` param to `LocalRunContext.__init__()` and verify snapshot side-effects are purely additive file writes that are safe to skip <!-- id: 102 -->
- [ ] **TuningAgent package** — Create `core/autotune/__init__.py`; implement `core/autotune/tuning_agent.py`: `TuningAgent.__init__(model_id, agents_config, temperature)`, `async generate_improved_prompt(current_prompt, judge_feedback, iteration, eval_dir) -> tuple[str, dict]`; load meta-prompt from `eval_dir/config/prompts/autotune.toml` with fallback to bundled template; emit OTel `autotune.tune` span; any `ProviderFactory` exception must propagate uncaught so `TuneStep.safe_execute()` classifies and applies `error_policy` (FR-7.2) <!-- id: 103 -->
- [ ] **Bundled meta-prompt** — Write `processors/autotune_template/autotune.toml` (v1): instructs LLM to analyze feedback, identify failure patterns, rewrite prompt preserving `{{placeholder_vars}}`, return improved prompt text only; uses all 7 `{{var}}` template variables from tech-design.md <!-- id: 104 -->
- [ ] **Package data** — Add `"gavel_ai": ["processors/autotune_template/*"]` entry to `[tool.setuptools.package-data]` in `pyproject.toml` (merge with existing `reporters/templates/*` entry) <!-- id: 105 -->
- [ ] **Unit tests — models** — Verify `EvalConfig` with `tuning` block parses; verify existing configs without `tuning` parse unchanged; verify `workflow_type: "autotune"` accepted <!-- id: 106 -->
- [ ] **Unit tests — CompositeStep** — `run_children()` returns `True` when all children succeed; returns `False` and stops on first child failure; error policy propagated correctly <!-- id: 107 -->
- [ ] **Unit tests — IterationEvalContext + LocalRunContext** — `get_prompt("name:v2")` reads `[v2]` from a tmp `prompts.toml`; falls back to base when `prompts.toml` absent; all other attributes delegate to base; `LocalRunContext(skip_snapshot=True)` skips config snapshot file writes <!-- id: 108 -->
- [ ] **Unit tests — TuningAgent** — `generate_improved_prompt()` calls `ProviderFactory` once with correct args; returns non-empty string; OTel span emitted <!-- id: 109 -->
- [ ] **Run unit tests** — `uv run pytest -m unit` passes green <!-- id: 110 -->
- [ ] **Open PR: Partition 1** → target `initiative/feat-autotune` <!-- id: 111 -->

---

## Partition 2: Engine → `feat/autotune-engine`

- [ ] **TuneStep** — Implement `core/steps/tune_step.py`: `phase = StepPhase.TUNING`; `execute(context: IterationRunContext)`: load current vN from outer `run_dir/prompts.toml`, aggregate full judge feedback from `context.run_dir/output_judged.jsonl` (all `{scenario_id, judge_name, score, reason}` records — no filtering), call `TuningAgent.generate_improved_prompt()`, validate `{{var}}` placeholder preservation (retry once on failure; abort iteration on second failure), append vN+1 with `avg_score` (0.0–1.0) to `prompts.toml`; do not catch `RunPolicyError` — let it propagate to `AutotuneWorkflow` (FR-7.2) <!-- id: 200 -->
- [ ] **Score normalization helper** — Add `normalize_score(score: float, judge_type: str) -> float` in `core/autotune/tuning_agent.py` or a new `core/autotune/scoring.py`: divides GEval scores by 10.0; passes deterministic (classifier/regression) 0/1 scores through unchanged <!-- id: 201 -->
- [ ] **AutotuneIterationStep** — Implement `core/steps/autotune_iteration_step.py`: subclasses `CompositeStep`; `child_steps = [ScenarioProcessorStep, JudgeRunnerStep, TuneStep]`; `execute(context: LocalRunContext)`: reads `TuningConfig` from `eval_ctx`; per iteration: creates `IterationEvalContext` + `IterationRunContext`, calls `run_children()` for ScenarioProcessorStep + JudgeRunnerStep, checks convergence, breaks if converged (skipping TuneStep), else calls `TuneStep.safe_execute()`, writes `IterationMetadata` (including `judge_scores` dict); emits `autotune.iteration` OTel span; writes `AutotuneRunSummary` on exit <!-- id: 202 -->
- [ ] **Convergence logic** — Implement `_check_convergence(iteration, current_score, previous_score, config) -> tuple[bool, Optional[str]]` on `AutotuneIterationStep`: four criteria in order — `max_rounds_reached`, `target_score_achieved`, `minimal_improvement`, `performance_degraded` <!-- id: 203 -->
- [ ] **AutotuneWorkflow** — Implement `core/workflows/autotune.py`: `async execute(resume_run_id=None) -> LocalRunContext`; PrepareStep: copy v1 prompt from `eval_ctx.get_prompt()` to `runs/<id>/prompts.toml`; orchestrate `[ValidatorStep, AutotuneIterationStep, ReportingStep]` via `safe_execute()`; resume: scan existing `iterations/iteration_N/metadata.json` files to determine last completed iteration, pass starting iteration to `AutotuneIterationStep` <!-- id: 204 -->
- [ ] **AutotuneReporter** — Implement `reporters/autotune_reporter.py`: subclasses `Jinja2Reporter`; `_build_context(run_summary: AutotuneRunSummary) -> dict`; passes iteration list, judge_scores breakdown, best iteration index, convergence reason, best prompt text + file path to template <!-- id: 205 -->
- [ ] **autotune.html template** — Implement `reporters/templates/autotune.html`: Run Summary header; Score Progression Table (one row per iteration, per-judge sub-columns, best row highlighted green); Per-Judge Detail expandable sections; Best Prompt Version section (inline copyable pre-block, file path, promotion instructions); no external JS/CSS dependencies <!-- id: 206 -->
- [ ] **Unit tests — TuneStep** — TOML write/read roundtrip with tmp_path; placeholder preservation validation triggers retry; missing placeholder after retry raises error; `avg_score` written on 0.0–1.0 scale <!-- id: 207 -->
- [ ] **Unit tests — convergence** — One test per criterion (4 total); verify correct `reason` string returned; verify `TuneStep` not called after convergence in the loop <!-- id: 208 -->
- [ ] **Unit tests — AutotuneReporter** — `_build_context()` produces correct structure from fixture `AutotuneRunSummary`; best iteration correctly identified <!-- id: 209 -->
- [ ] **Integration test** — `tests/integration/test_autotune_workflow.py`: scaffold real eval dir in `tmp_path`; mock `TuningAgent.generate_improved_prompt()` to return fixed improved prompt; run `AutotuneWorkflow` with `max_rounds=2`; assert `iterations/iteration_1/` and `iterations/iteration_2/` exist with `metadata.json` and `output_raw.jsonl`; assert `prompts.toml` has `[v1]` and `[v2]`; assert `run_summary.json` exists with correct `total_iterations=2`; assert `report.html` is non-empty; assert v2 prompt was used for iteration 2 scenarios (captured via mock LLM call) <!-- id: 210 -->
- [ ] **Run full test suite** — `uv run pytest -m unit && uv run pytest -m integration` passes green <!-- id: 211 -->
- [ ] **Open PR: Partition 2** → target `initiative/feat-autotune` <!-- id: 212 -->

---

## Partition 3: Surface → `feat/autotune-surface`

- [ ] **Autotune scaffolding** — Add `generate_autotune_templates(eval_root, eval_name)` to `cli/scaffolding.py`: writes `eval_config.json` (`workflow_type: "autotune"`, `tuning` block with documented defaults), `agents.json` template, `config/prompts/<eval-name>.toml` (v1 placeholder with `{{input}}`), `data/scenarios.json` (empty array) <!-- id: 300 -->
- [ ] **`gavel autotune create` command** — Implement in `cli/commands/autotune.py`: accepts `eval-name` positional arg and `--eval-root`; calls `generate_autotune_templates()`; refuses to overwrite existing eval dir without `--force`; prints next-step instructions on success <!-- id: 301 -->
- [ ] **`gavel autotune run` command** — Implement in `cli/commands/autotune.py`: `--eval` (required), `--eval-root`, `--run` (optional resume); resolves eval root via `cli/common.py::resolve_eval_root()`; constructs `LocalFileSystemEvalContext` and calls `AutotuneWorkflow.execute()`; prints Rich progress per iteration to stdout; prints report path on completion; prints Rich error panel to stderr on failure (matching oneshot error display pattern) <!-- id: 302 -->
- [ ] **Register command group** — Add `autotune` app to the main CLI in the appropriate entrypoint; verify `gavel --help` lists the `autotune` group <!-- id: 303 -->
- [ ] **Unit tests — CLI** — `gavel autotune create` happy path creates expected files; `gavel autotune create` (duplicate) exits non-zero; `gavel autotune run` with mocked workflow calls `AutotuneWorkflow.execute()` once <!-- id: 304 -->
- [ ] **Run full test suite** — `uv run pytest -m unit && uv run pytest -m integration` passes green <!-- id: 305 -->
- [ ] **Skill section** — Add autotune section to `gavel-skill/SKILL.md`: all 7 stages from tech-design.md §Skill Extension Specification — prerequisite check, config setup (with copy-pasteable JSON snippet), meta-prompt setup (available `{{var}}` variables), run command, report interpretation, prompt promotion steps, next-iteration guidance <!-- id: 306 -->
- [ ] **config-schema.md** — Update `skill/gavel-skill/references/config-schema.md`: add `tuning` block schema table (all `TuningConfig` fields with types, defaults, and 0.0–1.0 scale note); add `prompts.toml` format section <!-- id: 307 -->
- [ ] **cli-reference.md** — Run `uv run python scripts/update_cli_reference.py` (or equivalent) to regenerate `skill/gavel-skill/references/cli-reference.md` with the new `autotune create` and `autotune run` commands <!-- id: 308 -->
- [ ] **Manual smoke test** — Run `gavel autotune create smoke-test`, inspect scaffolded files, run `gavel autotune run --eval smoke-test` against a real LLM with `max_rounds=1`; confirm report.html renders correctly in browser <!-- id: 309 --> <!-- NEEDS MANUAL REVIEW -->
- [ ] **Open PR: Partition 3** → target `initiative/feat-autotune` <!-- id: 310 -->

---

## Initiative Completion

- [ ] **Merge initiative to master** — Merge `initiative/feat-autotune` → `master` via PR <!-- id: 400 -->
- [ ] **Synthesize canon** — Update `canon/tech-overview.md`, `canon/summary.md` with autotune workflow, new modules, `TuningConfig` conventions, score normalization, and `{{var}}` meta-prompt template variables <!-- id: 401 -->
- [ ] **Archive** — `cicadas.py archive feat-autotune --type initiative` <!-- id: 402 -->
