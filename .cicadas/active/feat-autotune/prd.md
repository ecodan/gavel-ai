---
summary: "Autotune implements automated iterative prompt optimization in gavel-ai using an LLM-as-meta-optimizer (TuningAgent). Starting from an initial prompt (v1), it runs a loop — execute scenarios → judge outputs → generate improved prompt (vN+1) — until a configurable convergence criterion is met. Includes an agent skill extension (autotune section in gavel-skill) so an AI agent can walk a user through the complete autotune setup and run process end-to-end. Targets prompt engineers and ML practitioners who want to improve prompt quality without manual trial-and-error."
phase: "clarify"
when_to_load:
  - "When defining or reviewing autotune goals, users, scope, success criteria, and risks."
  - "When validating that implementation aligns with intended optimization workflow."
depends_on: []
modules:
  - "cli/commands/autotune.py"
  - "core/workflows/"
  - "core/steps/"
  - "models/config.py"
  - "reporters/"
  - "providers/"
  - "src/gavel_ai/skill/gavel-skill/SKILL.md"
  - "src/gavel_ai/skill/gavel-skill/references/"
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
next_section: null
---

# PRD: feat-autotune

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

---

## Executive Summary

Autotune extends gavel-ai with automated iterative prompt optimization. Given an initial prompt (v1) and a judge suite, it runs a loop — execute scenarios → judge outputs → generate an improved prompt (vN+1) via a TuningAgent (LLM-as-meta-optimizer) — repeating until a convergence criterion is met or the maximum number of rounds is reached. The result is a versioned prompt history, a score progression chart, and a final HTML report comparing all iterations.

### What Makes This Special

- **Zero manual iteration** — The TuningAgent analyzes judge feedback and writes the next prompt automatically, eliminating the "edit, re-run, compare" cycle.
- **Reuses the full gavel-ai evaluation stack** — Autotune is an orchestration layer over existing `ScenarioProcessorStep` and `JudgeRunnerStep`; no evaluation logic is duplicated.
- **Configurable convergence** — Four stopping criteria (target score, minimal improvement, score degradation, max rounds) give users precise control over cost vs. quality trade-offs.
- **Agent skill enabled** — An AI agent (e.g., Claude Code) can guide a user through the complete autotune setup and run process end-to-end by invoking the gavel skill, with no prior knowledge of the config format required.

---

## Project Classification

**Technical Type:** Developer Tool (CLI extension to an existing eval framework)
**Domain:** ML / LLMOps / Prompt Engineering
**Complexity:** High — async iteration loop, LLM meta-optimizer, TOML prompt versioning, resume capability, HTML report
**Project Context:** Brownfield — gavel-ai already has OneShot and Conversational workflows, step-based orchestration, provider abstraction, and a Jinja2 reporter. Autotune builds on all of these. The `cli/commands/autotune.py` stub already exists with `create` and `run` commands printing "Implementation pending."

---

## Success Criteria

### User Success

A user achieves success when they can:

1. **Run a complete autotune optimization end-to-end** — `gavel autotune create my_eval` then `gavel autotune run --eval my_eval` produces an improved prompt and a report without manual intervention.
2. **Understand which iteration won and why** — The HTML report clearly shows score progression, which iteration scored highest, and why optimization stopped.
3. **Resume an interrupted run** — `gavel autotune run --eval my_eval --run <id>` picks up from the last completed iteration without reprocessing earlier ones.

### Technical Success

The system is successful when:

1. **All four convergence criteria are correctly detected** and the reason is recorded in `run_metadata.json`.
2. **Prompt versions are faithfully preserved** in `runs/<id>/prompts.toml` with per-version metadata (iteration number, average score).
3. **Unit test coverage ≥ 80%** on all new autotune modules.
4. **Integration test** executes a full 2-iteration loop against a mocked LLM and produces valid `output_raw.jsonl`, `output_judged.jsonl`, and `report.html`.
5. **Agent can guide a user from zero to a completed autotune run** using only the gavel skill — the skill's autotune section covers all stages, troubleshooting, and report interpretation without requiring external docs.

### Measurable Outcomes

- 5-iteration optimization over 10 scenarios completes in < 5 minutes (using existing async parallelism, 10 concurrent).
- TuningAgent overhead ≤ 10 s per iteration.
- `gavel autotune create` produces a runnable scaffold in < 1 s.

---

## User Journeys

### Journey 1: Prompt Engineer — First Automated Optimization

Sarah is a prompt engineer at a mid-sized SaaS company. She has been manually tweaking a customer-support summarization prompt for three days, running gavel oneshot after each edit and comparing scores by hand. She discovers that gavel now has `autotune`, scaffolds a new eval, drops in her prompt as `v1`, configures two GEval judges (accuracy, conciseness), and sets `max_rounds: 5`. She runs `gavel autotune run`, grabs a coffee, and comes back to an HTML report showing that `v3` achieved the best score (0.87) and that the improvement plateaued after that. She exports `v3` from `prompts.toml` and deploys it.

**Requirements Revealed:** scaffold command, configurable judges, per-iteration artifact storage, HTML report with best-iteration highlight, prompts.toml export.

---

### Journey 2: ML Engineer — Convergence Tuning on a Budget

Marcus is running autotune on a cost-sensitive project. He sets `target_score: 0.85` and `degradation_tolerance: 0.05` to stop as soon as quality is good enough or deteriorates. After iteration 2 the score hits 0.86, optimization stops, and the report shows "target_score_achieved." He is billed for exactly 2 iterations of LLM calls instead of the default 5.

**Requirements Revealed:** target_score convergence, degradation_tolerance, convergence_reason in report.

---

### Journey 3: Researcher — Resume After Crash

Priya is running a 10-round optimization overnight. The process is killed at iteration 6 by an OOM event. She runs `gavel autotune run --eval my_eval --run 20250601_002000` and the system detects iterations 1–6 already completed, resumes from iteration 7, and finishes. The final report includes all 10 iterations.

**Requirements Revealed:** resume via --run flag, iteration metadata persistence, report aggregates across sessions.

---

### Journey 4: Developer — Agent-Guided Setup

Alex is a backend engineer who needs to optimize a classification prompt but has never used gavel before. He invokes the gavel skill in Claude Code and says "help me set up an autotune eval." The skill walks him through: `gavel init`, formatting his scenarios, running `gavel autotune create`, filling in `agents.json` (including choosing a tuning agent model), selecting and configuring judges, setting convergence parameters, and finally running `gavel autotune run`. At each stage the skill writes or edits the relevant config file on his behalf and explains what it did. Alex never has to open the documentation — the agent handles everything conversationally.

**Requirements Revealed:** autotune skill section (full 7-stage guided flow), skill-readable reference docs for autotune config schema and CLI, skill support for interpreting autotune reports and convergence output.

---

### Journey Requirements Summary

| User Type | Key Requirements |
|-----------|-----------------|
| **Prompt Engineer (Sarah)** | scaffold, judges, per-iteration artifacts, HTML report, prompts.toml |
| **ML Engineer (Marcus)** | target_score, degradation_tolerance, convergence_reason |
| **Researcher (Priya)** | --run resume flag, iteration metadata, cross-session report |
| **Developer (Alex)** | autotune skill guided setup flow, reference docs, report interpretation via skill |

---

## Scope

### MVP — Minimum Viable Product (v1)

**Core Deliverables:**
- `TuningConfig` model (fields: `max_rounds`, `convergence_threshold`, `target_score`, `degradation_tolerance`, `tuning_agent_model`, `tuning_agent_temperature`)
- `TuningAgent` — LLM-as-meta-optimizer using existing provider factory; loads meta-prompt from eval dir with bundled fallback
- `TuneStep` — workflow step that loads prompt vN, aggregates judge feedback, calls TuningAgent, appends vN+1 to `prompts.toml`
- `AutotuneIterationStep` — CompositeStep running the loop (ProcessingStep → JudgeRunnerStep → TuneStep) with convergence checking
- `AutotuneWorkflow` — BaseWorkflow subclass (PrepareStep → ValidateStep → AutotuneIterationStep → ReportingStep)
- Autotune HTML reporter (Jinja2 template: score progression, side-by-side prompt versions, best iteration highlighted, convergence reason)
- `gavel autotune create` — scaffold eval directory with tuning config template and initial `prompts.toml`
- `gavel autotune run [--eval NAME] [--run ID]` — execute or resume AutotuneWorkflow
- **Agent skill extension** — autotune section added to `gavel-skill/SKILL.md` covering the full guided setup flow (7 stages); updated reference docs (`cli-reference.md`, `config-schema.md`) to include autotune commands and `tuning` config fields
- Unit tests (≥ 80% coverage on new modules) and integration test (2-iteration mocked loop)

**Quality Gates:**
- `uv run pytest -m unit` passes
- `uv run pytest -m integration` passes
- `uv run mypy src/` passes on new modules
- `uv run ruff check src/` passes

### Growth Features (Post-MVP)

**v2: Advanced Optimization Strategies**
- Parallel variant exploration (test multiple prompt variants per iteration, pick best)
- Multi-objective optimization (optimize weighted combination of multiple judge scores)
- `gavel autotune report --eval NAME --run ID` (regenerate report without re-running)

**v3: Collaboration and Observability**
- Interactive mode — human approval gate before applying each prompt update
- Cost tracking — token usage and estimated API cost per iteration surfaced in report
- Ensemble tuning — multiple TuningAgents vote on improvements

### Vision (Future)

- Transfer learning — use successful optimizations as seed prompts for new evaluations
- Bayesian convergence — statistical significance testing instead of fixed threshold
- Prompt diff viewer — visual side-by-side diff of prompt changes between versions

---

## Functional Requirements

### 1. Configuration

**FR-1.1:** The system must support a `tuning` section in `eval_config.json` with the following fields:
- `max_rounds: int` — hard upper bound on iterations (required)
- `convergence_threshold: float` — stop if `|current_score − previous_score| < threshold` (required)
- `target_score: float | null` — stop early if current score ≥ target (optional)
- `degradation_tolerance: float` — stop if score drops by more than tolerance (default 0.2)
- `tuning_agent_model: str` — model ID from `agents.json` to use for TuningAgent (required)
- `tuning_agent_temperature: float` — temperature for TuningAgent calls (default 0.7)

**FR-1.2:** The `gavel autotune create <name>` command must scaffold a runnable eval directory including a `tuning` section in `eval_config.json` with sensible defaults and an initial prompt file (`prompts/<name>.toml` with `[v1]`).

**FR-1.3:** Users may provide a custom meta-prompt at `config/prompts/autotune.toml`; the system falls back to the bundled default template if absent.

---

### 2. Iteration Execution

**FR-2.1:** The `AutotuneIterationStep` must execute the following sequence per iteration: `ScenarioProcessorStep` (with iteration-specific output dir) → `JudgeRunnerStep` (reading from that dir) → convergence check → `TuneStep` (if not converged).

**FR-2.2:** Each iteration must write its artifacts to `runs/<id>/iterations/iteration_<N>/`: `output_raw.jsonl`, `output_judged.jsonl`, `metadata.json`. The outer run directory must also contain `run_summary.json` (written on loop exit) with the full `AutotuneRunSummary` used by the reporter.

**FR-2.3:** `metadata.json` per iteration must record: `iteration`, `score` (0.0–1.0), `improvement`, `converged`, `convergence_reason`, `prompt_version`, `judge_scores` (dict of per-judge mean scores, 0.0–1.0).

**FR-2.4:** All generated prompt versions must be appended to `runs/<id>/prompts.toml` in the format:
```toml
[v2]
prompt = "..."
iteration = 1
avg_score = 0.75   # normalized 0.0–1.0
```

---

### 3. Convergence Detection

**FR-3.1:** After each iteration the system must evaluate all four criteria in order and stop on the first match:
1. `iteration >= max_rounds` → reason: `max_rounds_reached`
2. `current_score >= target_score` (if set) → reason: `target_score_achieved`
3. `iteration > 1` and `|current_score − previous_score| < convergence_threshold` → reason: `minimal_improvement`
4. `iteration > 1` and `previous_score − current_score > degradation_tolerance` → reason: `performance_degraded`

**FR-3.2:** Convergence reason must be written to `run_metadata.json` and surfaced in the HTML report.

---

### 4. TuningAgent

**FR-4.1:** `TuningAgent.generate_improved_prompt(current_prompt, judge_feedback, iteration)` must return `(improved_prompt_text, analysis_metadata)`.

**FR-4.2:** The agent must preserve all `{{var}}`-style placeholder variables from the original prompt in the generated version. If any placeholder is missing from the generated text, the agent must retry once; if still missing after retry, it must abort the iteration with an error.

**FR-4.3:** The agent must pass the full judge feedback (all `{scenario_id, judge_name, score, reason}` records) as a JSON list to the meta-prompt. No frequency filtering — the meta-prompt template is responsible for synthesizing the feedback.

**FR-4.4:** The agent must parse the improved prompt from the LLM response using: explicit `IMPROVED PROMPT:` marker first, then code-fenced block, then full response as fallback.

---

### 5. Resume Capability

**FR-5.1:** `gavel autotune run --eval NAME --run ID` must detect existing iteration directories for the given run ID, load the last completed iteration's score, and continue from the next iteration.

**FR-5.2:** The resume path must not re-execute already-completed iterations.

---

### 6. Reporting

**FR-6.1:** After the iteration loop completes, the system must generate an HTML report at `runs/<id>/report.html` containing:
- Optimization summary (total iterations, convergence status, best score)
- Score progression (per-iteration scores in a table or chart)
- Side-by-side prompt version comparison
- Best iteration clearly highlighted
- Convergence analysis (reason for stopping)

**FR-6.2:** The report must be self-contained (single HTML file, no external dependencies).

---

### 7. Error Handling

**FR-7.1:** Per-scenario failures within an iteration must be logged but must not abort the iteration; scores are computed from successful scenarios only.

**FR-7.2:** TuningAgent generation failures must abort the current iteration and surface the error per the existing `error_policy` pattern (`error_policy.should_halt(tier)`).

**FR-7.3:** Errors must be displayed as Rich panels to stderr with human-readable cause and path to `run.log`; no raw stack traces to terminal.

---

### 8. Agent Skill (Guided Setup)

**FR-8.1:** `gavel-skill/SKILL.md` must include an autotune section that maps user intent "set up autotune" / "run autotune" / "interpret autotune results" to a 7-stage guided flow:
1. Initialize project (`gavel init` if needed)
2. Prepare or reuse scenarios
3. Create scaffold (`gavel autotune create <name>`)
4. Configure `agents.json` — including selecting and configuring the `tuning_agent_model`
5. Configure judges for scoring each iteration
6. Set tuning convergence parameters (`max_rounds`, `convergence_threshold`, `target_score`, `degradation_tolerance`)
7. Run the optimization (`gavel autotune run --eval <name>`) and monitor output

**FR-8.2:** The skill must be able to write or edit all autotune-specific config files on the user's behalf: `eval_config.json` (including `tuning` section), `agents.json`, judge config, and the initial `prompts/<name>.toml`.

**FR-8.3:** The skill must include a troubleshooting table for autotune-specific failure modes (e.g., TuningAgent prompt parse failure, missing `tuning_agent_model` in `agents.json`, `max_rounds: 0` misconfiguration, placeholder variable stripped from generated prompt).

**FR-8.4:** The skill must be able to interpret and explain an autotune report to the user: score progression, which iteration scored best, convergence reason, and how to apply the best prompt version.

**FR-8.5:** `gavel-skill/references/cli-reference.md` must be updated (via `scripts/update_cli_reference.py`) to include `gavel autotune create` and `gavel autotune run` with all options and envvars.

**FR-8.6:** `gavel-skill/references/config-schema.md` must be updated to document the `tuning` section of `eval_config.json` and the `prompts.toml` versioned format produced by autotune runs.

---

## Non-Functional Requirements

- **Performance:** 5-iteration run over 10 scenarios completes in < 5 minutes at `max_concurrent: 10`. TuningAgent overhead ≤ 10 s per iteration.
- **Reliability:** Iteration artifacts written atomically. Resume must be lossless for completed iterations. Partial failures (some scenarios fail) do not crash the iteration.
- **Security:** Meta-prompt user customization file treated as untrusted input — no eval() or exec() on its contents. Provider credentials handled exclusively by existing `ProviderFactory`.
- **Maintainability:** New modules carry type hints on all public APIs. `ScenarioProcessorStep` and `JudgeRunnerStep` must not be modified to add autotune-specific logic — all iteration awareness injected via configuration only. Test coverage ≥ 80% on new code.

---

## Open Questions

- **Q1 (Decision — implementation):** Should `AutotuneIterationStep` inherit from a new `CompositeStep` base class (as described in TDD), or simply be a regular `Step` that internally loops over child steps? The existing codebase has no `CompositeStep`; adding one has overhead. **Recommended:** start as a plain Step with an internal loop; introduce CompositeStep only if a second composite step is needed.
- **Q2 (Decision — UX):** Should the `autotune create` scaffold generate a `prompts.toml` copy in the eval's `config/prompts/` dir (matching OneShot convention) or write directly to `runs/<id>/prompts.toml` at run time? **Recommended:** scaffold writes initial `v1` to `config/prompts/<name>.toml`; run copies it to `runs/<id>/prompts.toml` as PrepareStep.
- **Q3 (Dependency):** The TDD references `toml` (write) and `tomllib` (read). `tomllib` is stdlib (Python 3.11+). `toml` (write) may need to be added as a dependency — check if `tomli-w` or another writer is preferred given existing deps.

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| TuningAgent produces prompts that drop `{{var}}` placeholders | Medium | High | Validate that all original `{{var}}` placeholders appear in generated prompt; if not, retry once then abort iteration |
| LLM response parsing fails to extract improved prompt | Medium | Medium | Three-strategy fallback (marker → code fence → raw response); log warning on fallback |
| Long iteration runs consume excessive API budget | Medium | Medium | `max_rounds` is required and enforced; document cost estimates in scaffold |
| Resume logic misidentifies completed iterations | Low | High | Detect completion by presence of both `output_judged.jsonl` AND `metadata.json` in iteration dir |
| Existing `ScenarioProcessorStep` / `JudgeRunnerStep` need changes for iteration-aware I/O | Medium | Medium | Design iteration config as a pass-through parameter; avoid modifying step internals |
| Skill reference docs drift from actual CLI / config schema | Medium | Medium | `scripts/update_cli_reference.py` regenerates `cli-reference.md` from live help output; `config-schema.md` updated as part of the same PR as config model changes |
| Skill autotune flow covers too many edge cases and becomes bloated | Low | Low | Keep skill flow at 7 stages matching the existing oneshot skill pattern; troubleshooting table is additive and doesn't enlarge the happy path |
