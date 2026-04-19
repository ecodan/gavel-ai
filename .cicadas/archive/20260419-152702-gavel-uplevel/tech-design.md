---
summary: "gavel-uplevel extends the existing judge and pipeline infrastructure incrementally. The large majority of the 11 FR areas are already implemented; the remaining work is four new DeepEval judge types, markdown_path judge config loading, judge criteria templating ({{key}} substitution), and schema documentation. All new code follows the established Judge/DeterministicMetric/Step base-class patterns and the LocalFileSystemEvalContext/LocalRunContext storage model."
phase: "tech"
when_to_load:
  - "When implementing or reviewing architecture, interfaces, data models, conventions, and sequencing."
  - "When checking whether changes still conform to the agreed technical approach."
depends_on:
  - "prd.md"
modules:
  - "src/gavel_ai/judges/"
  - "src/gavel_ai/core/steps/judge_runner.py"
  - "src/gavel_ai/reporters/oneshot_reporter.py"
  - "docs/specs/"
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

# Tech Design: gavel-uplevel

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

**Summary:** The gavel-uplevel initiative delivers 11 capability areas targeting judge quality, config ergonomics, and pipeline correctness. A significant portion of these areas — deterministic judges (ClassifierMetric/RegressionMetric), external TOML judge config resolution, config snapshot with prompts, step completion tracking, validator hardening, error score exclusion, and scaffold templates for classification/regression — were implemented as part of the prior `report-upgrades` initiative and are already present in the codebase. The remaining work is narrowly scoped: adding four missing DeepEval judge types to `JUDGE_TYPE_MAP`, implementing `markdown_path` judge config loading, adding `{{key}}` criteria templating in the judge runner, and authoring schema documentation.

The architecture is already established and must be followed without deviation: judges extend `Judge` (LLM) or `DeterministicMetric` (zero-LLM), steps extend `Step`, config access goes through `LocalFileSystemEvalContext`, and run artifacts go through `LocalRunContext`. No new architectural patterns are introduced.

### Cross-Cutting Concerns

1. **Brownfield invariance** — Every change must leave existing `pytest -m unit` and `pytest -m integration` test suites green. No method signatures, file formats, or storage paths may change without migration.
2. **Import safety for optional deps** — `scikit-learn` is already in dependencies; `deepeval` is optional. New DeepEval judge types must guard their imports inside `JUDGE_TYPE_MAP` initialization identically to the existing pattern.
3. **Path safety for external file loading** — Any file resolved from user-supplied strings (judge config name, markdown path) must be validated to lie within `eval_ctx.eval_dir` before opening.

### Brownfield Notes

The following are **already implemented** and must not be re-implemented or regressed:

| FR | Location | Status |
|----|----------|--------|
| FR-1: DeterministicMetric, ClassifierMetric, RegressionMetric | `judges/deterministic_metric.py` | ✓ Done |
| FR-1.5: Batch finalization (compute() called in judge_runner) | `core/steps/judge_runner.py` | ✓ Done |
| FR-1.6: JudgeRegistry registration ("classifier", "regression") | `judges/deterministic_metric.py` bottom | ✓ Done |
| FR-3.1/3.2: `config_ref` → TOML resolution via `get_judge_config()` | `core/steps/judge_runner.py:171`, `core/contexts.py:379` | ✓ Done |
| FR-4: `snapshot_run_config()` with prompts + metadata | `core/contexts.py:558` | ✓ Done |
| FR-6: Reporter deterministic section, skipped_counts | `reporters/oneshot_reporter.py` | ✓ Done |
| FR-7: `--template classification/regression` scaffold | `cli/scaffolding.py`, `cli/commands/oneshot.py` | ✓ Done |
| FR-8: ValidatorStep with all checks | `core/steps/validator.py` | ✓ Done |
| FR-9: `mark_step_complete()`, `get_completed_steps()`, `StepPhase.PREPARE` | `core/contexts.py:615`, `core/steps/base.py` | ✓ Done |
| FR-10: Error output exclusion from score averages | `reporters/oneshot_reporter.py` | ✓ Done |

**Remaining gaps:**

| FR | Gap | Location to modify |
|----|-----|-------------------|
| FR-2 | 4 missing DeepEval judge types | `judges/deepeval_judge.py` |
| FR-3.3 | `markdown_path` judge config loading | `core/steps/judge_runner.py` |
| FR-5 | Schema documentation | `docs/specs/` (new files) |
| FR-11 | Judge criteria `{{key}}` templating | `core/steps/judge_runner.py` |

---

## Tech Stack & Dependencies

| Category | Selection | Rationale |
|----------|-----------|-----------|
| Language | Python 3.13+ | Existing project standard |
| Frameworks | Typer (CLI), Pydantic v2 (models), Jinja2 (reports) | Already in use |
| Judge eval | deepeval (optional) | Existing pattern |
| Deterministic metrics | scikit-learn | Already added; used by ClassifierMetric/RegressionMetric |
| TOML parsing | `toml` library | Already used in `get_judge_config()` |
| Testing | pytest with `unit` / `integration` markers | Existing pattern |

**New dependencies introduced:** None — `scikit-learn` and `toml` are already present.

**Dependencies explicitly rejected:**
- `Jinja2` for criteria templating — FR-11 explicitly requires no third-party templating library; use a simple `str.replace()` loop.

---

## Project / Module Structure

Changes are narrowly scoped to four areas:

```
src/gavel_ai/
├── judges/
│   └── deepeval_judge.py       # [MODIFIED] Add 4 types to JUDGE_TYPE_MAP
├── core/
│   └── steps/
│       └── judge_runner.py     # [MODIFIED] Add markdown_path loading + criteria templating
docs/
└── specs/                      # [NEW directory]
    ├── schema-configs.md        # NEW: eval_config.json, agents.json, scenarios.json field reference
    └── schema-outputs.md        # NEW: results_raw.jsonl, results_judged.jsonl, .config/ structure
```

No new Python modules. No new CLI commands. No new data sources or storage paths.

**Key structural decisions:**
- Criteria templating lives in `judge_runner.py` (not in `deepeval_judge.py` or a new util module) — it is a pre-processing step that resolves judge config before the judge sees it, keeping judge classes pure.
- `markdown_path` loading is also handled in `judge_runner.py` at the config resolution stage, alongside `config_ref`, for consistency.

---

## Architecture Decisions (ADRs)

### ADR-1: Criteria Templating in judge_runner, not in judge classes

**Decision:** `{{key}}` substitution on `criteria` and `evaluation_steps` is performed in `judge_runner.py` during the judge config resolution stage, before the judge object is constructed.

**Rationale:** Judge classes (`DeepEvalJudge`, `GEval`) should not carry scenario context awareness. Resolving templates at the runner level keeps judge classes stateless, reusable across scenarios, and independently testable. The runner already owns the scenario object and judge config at this point — no new dependencies are needed.

**Affects:** `core/steps/judge_runner.py` (add `_render_judge_template()` helper and call it after config resolution)

---

### ADR-2: `markdown_path` Parsing is inline in judge_runner, not a new context method

**Decision:** When a judge entry has `markdown_path`, the file is read and parsed in `judge_runner.py` rather than adding a `get_judge_markdown()` method to `LocalFileSystemEvalContext`.

**Rationale:** Markdown rubric loading is a one-off parsing concern, not a general-purpose config access pattern. Adding it to `EvalContext` ABC would require updating the abstract class and every implementation, introducing interface churn for a niche feature. The runner reads the file directly (after path safety check) and merges the parsed sections into the judge config dict. This is consistent with how `config_ref` was implemented using `get_judge_config()` on the eval context — if the pattern were to expand to many more file types, a context method would be warranted, but it isn't warranted yet.

**Affects:** `core/steps/judge_runner.py` (add `_load_markdown_judge_config()` helper)

---

### ADR-3: DeepEval types guarded by try/except at module level

**Decision:** The four new DeepEval types (ToxicityMetric, ConversationCompletenessMetric, ConversationalGEval, TurnRelevancyMetric) are added to `JUDGE_TYPE_MAP` inside the existing `try: from deepeval... except ImportError: pass` block.

**Rationale:** The existing DeepEval judge types follow this pattern. Maintaining it means the module loads safely when deepeval is not installed, and all types fail with the same informative error at runtime. Changing to lazy imports or a different guard pattern would create two code paths for the same concern.

**Affects:** `judges/deepeval_judge.py` (`JUDGE_TYPE_MAP` block and import list)

---

### ADR-4: Schema docs are Markdown in docs/specs/, not auto-generated

**Decision:** `schema-configs.md` and `schema-outputs.md` are hand-authored Markdown files in `docs/specs/`, not generated from Pydantic models.

**Rationale:** Auto-generated docs would require a doc-gen toolchain (pdoc, mkdocs, etc.) that doesn't exist in this project. Hand-authored docs can include human intent, examples, and usage context that field-level type annotations cannot. They also won't silently diverge the moment a docstring is missing. The risk of staleness is accepted in exchange for authoring simplicity — the `CLAUDE.md` reference requirement keeps them discoverable.

**Affects:** `docs/specs/` (new files), `CLAUDE.md` (add reference links)

---

### ADR-5: `_render_judge_template()` uses simple string replacement, not regex

**Decision:** Template substitution replaces `{{key}}` by iterating over context keys and calling `template.replace(f"{{{{{key}}}}}", value)`. Missing keys leave the placeholder unchanged; no regex is used.

**Rationale:** Regex introduces failure modes (catastrophic backtracking, greedy match edge cases) for a feature whose spec explicitly says "no third-party templating library" and "missing keys leave `{{key}}` in place." Simple string replacement satisfies all acceptance criteria with zero risk of template injection or silent data corruption.

**Affects:** `core/steps/judge_runner.py`

---

## Data Models

### New Models

None — all model types needed are already defined.

### Modified Models

None — no Pydantic model fields are added or changed.

The `JudgeConfig` model already has `config_ref: Optional[str]` and `config: Optional[Dict[str, Any]]`. The `markdown_path` field needs to be verified or added:

| Model | Change | Migration Required? |
|-------|--------|-------------------|
| `JudgeConfig` (`models/config.py`) | Verify `markdown_path: Optional[str]` field exists; add if absent | No — additive, defaults to None |

If `markdown_path` is absent from `JudgeConfig`, add it as an optional field with `None` default. This is a purely additive Pydantic model change — no migration needed.

---

## API & Interface Design

### New CLI Commands / Options

No new commands. All scaffold templates are already wired (`--template classification/regression`).

### New Internal Interfaces

#### `_render_judge_template(template: str, context: dict) -> str`

Private helper in `judge_runner.py`:

```python
def _render_judge_template(template: str, context: dict[str, Any]) -> str:
    result = template
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result
```

Called after judge config is resolved (inline or from `config_ref`/`markdown_path`) and before the judge object is created. Applied to both `criteria` (str) and `evaluation_steps` (list[str]).

#### `_load_markdown_judge_config(markdown_path: Path) -> dict`

Private helper in `judge_runner.py`. Reads a Markdown file and parses named sections:

```
## Criteria        → dict key "criteria"
## Evaluation Steps → dict key "evaluation_steps" (list split by "\n- ")
## Threshold       → dict key "threshold" (float)
## Guidelines      → dict key "guidelines" (str)
```

Missing sections silently default to absent keys (not empty strings).

Path safety check: resolved path must be under `eval_ctx.eval_dir`. If not, raise `ConfigError`.

#### Markdown Judge Config Format

```markdown
## Criteria
The response must accurately address the user's question without hallucinating facts.

## Evaluation Steps
- Check that all factual claims are grounded in the provided context.
- Verify no external knowledge is introduced without clear labeling.

## Threshold
0.75

## Guidelines
Apply strict factual grounding. Penalize any unverifiable claim.
```

### Backward Compatibility

All changes are additive:
- New `JUDGE_TYPE_MAP` entries don't affect existing judge type lookups.
- `markdown_path` is a new optional field — existing configs without it are unaffected.
- Criteria templating only applies when `{{` appears in a criteria string — configs without templates are unchanged.
- Schema docs are new files; no existing files change.

---

## Implementation Patterns & Conventions

### Naming Conventions

| Construct | Convention | Example |
|-----------|-----------|---------|
| Private helpers in steps | `_snake_case` | `_render_judge_template()` |
| Judge type keys | `"deepeval.{metric_name}"` | `"deepeval.toxicity"` |
| Section headings in Markdown rubrics | `## Title Case` | `## Criteria` |

### Error Handling Pattern

Follow the established pattern in `judge_runner.py`:

```python
# Config errors → ConfigError (propagates up, terminates run)
raise ConfigError(f"Judge config '{name}': {reason} - {actionable_fix}")

# Soft failures (missing template key) → log debug, leave placeholder
logger.debug(f"Judge criteria template key '{{key}}' not found in scenario context — leaving in place")
```

**Rules:**
- `ConfigError` for file-not-found, malformed TOML/Markdown, invalid field types.
- Silent pass-through (with debug log) for missing `{{key}}` substitution — never crash on missing template vars.
- Path traversal attempts → `ConfigError` (never silently skip).

### Testing Pattern

```python
# Unit test pattern for criteria templating
def test_render_judge_template_substitutes_known_keys():
    result = _render_judge_template("Evaluate {{category}} response", {"category": "billing"})
    assert result == "Evaluate billing response"

def test_render_judge_template_leaves_unknown_keys():
    result = _render_judge_template("Check {{unknown}}", {})
    assert result == "Check {{unknown}}"
```

**Coverage expectations:** All new helpers covered by unit tests. DeepEval judge types covered by unit tests using mocked `deepeval` metrics (consistent with existing `test_deepeval_judge.py` pattern).

**Mocking strategy:** Mock `deepeval` metric classes at the class level in unit tests; use real filesystem and real Pydantic models everywhere else.

---

## Security & Performance

### Security

| Concern | Mitigation |
|---------|-----------|
| `markdown_path` path traversal | Resolve to absolute path; assert `resolved.is_relative_to(eval_ctx.eval_dir)` before `open()` — raise `ConfigError` if check fails |
| `config_ref` path traversal | Already mitigated by `get_judge_config()` in `LocalFileSystemEvalContext` which constructs the path from `config_dir / "judges" / f"{name}.toml"` — no user-controlled path segment |
| Criteria template injection | `_render_judge_template` performs string replacement only; no `eval()`, no shell execution |

### Performance

| Concern | Target | Approach |
|---------|--------|---------|
| Criteria templating overhead | < 1ms per judge per scenario | String replacement on short strings; no compiled regex |
| Markdown file loading | < 5ms per judge config | Single file read + line scan; cached after first load (add to `_judge_config_cache` pattern) |
| New DeepEval types | Same as existing types | No behavior change — same async evaluate() path |

### Observability

No new logging or tracing is required beyond what exists. The `judge_runner.py` already logs judge config resolution at DEBUG level — extend that log to note when criteria templating is applied.

---

## Implementation Sequence

The four remaining gaps have no dependencies on each other and can be implemented in any order or in parallel.

1. **FR-2: DeepEval judge types** *(isolated, low-risk)* — Add 4 import lines and 4 `JUDGE_TYPE_MAP` entries in `judges/deepeval_judge.py`. Add unit tests.

2. **FR-11: Judge criteria templating** *(isolated, no model changes)* — Add `_render_judge_template()` helper and call sites in `judge_runner.py`. Add unit tests.

3. **FR-3.3: `markdown_path` loading** *(depends on verifying `JudgeConfig.markdown_path` field)* — Verify/add `markdown_path` field to `JudgeConfig`; add `_load_markdown_judge_config()` helper in `judge_runner.py`; add path safety check; add unit tests.

4. **FR-5: Schema docs** *(independent, no code changes)* — Author `docs/specs/schema-configs.md` and `docs/specs/schema-outputs.md`; add references in `CLAUDE.md`.

**Parallel work opportunities:** All four items are fully independent. A single implementor should start with FR-2 (smallest change, highest confidence) to establish momentum, then FR-11, then FR-3.3, then FR-5.

**Known implementation risks:**
- `deepeval` imports for the 4 new types — verify that `ToxicityMetric`, `ConversationCompletenessMetric`, `ConversationalGEval`, and `TurnRelevancyMetric` are importable from the version of `deepeval` pinned in `pyproject.toml`. If any are unavailable, stub the type behind a conditional guard with a clear `ConfigError` message.
- `JudgeConfig.markdown_path` field — read `models/config.py` first to confirm whether the field already exists. If absent, it's a one-line Pydantic addition; if present, no change needed.
