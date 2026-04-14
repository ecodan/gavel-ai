
---
summary: "Extend OneShotReporter._build_context to pass execution time, test-subject info, input source, and scenario count to the template. Update ReportRunnerStep to include those fields in RunData.metadata. Rewrite oneshot.html template sections: header (add execution time + eval label), Eval Summary (split LLM and deterministic sub-tables per subject), Performance Summary (add subject sub-header), Scenario Detail (table layout, collapsible inputs, truncated responses). No new Python dependencies. No breaking changes to ReportData model."
phase: "tech"
when_to_load:
  - "When implementing or reviewing architecture, interfaces, data models, conventions, and sequencing."
  - "When checking whether changes still conform to the agreed technical approach."
depends_on:
  - "prd.md"
  - "ux.md"
modules:
  - "src/gavel_ai/reporters/templates/oneshot.html"
  - "src/gavel_ai/reporters/oneshot_reporter.py"
  - "src/gavel_ai/core/steps/report_runner.py"
  - "src/gavel_ai/models/runtime.py"
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
next_section: "done"
---

# Tech Design: Report Upgrades

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

**Summary:** The report pipeline is a three-layer stack: `ReportRunnerStep` assembles a `RunData` dataclass and calls `OneShotReporter.generate()`; `OneShotReporter._build_context()` converts `RunData` into a flat dict for Jinja2; `oneshot.html` renders that dict into HTML. The gaps all live in either the dict assembly (missing fields) or the template (missing/wrong sections). The fix is additive: extend `RunData.metadata`, `_build_context`, and the template. The existing `ReportData` Pydantic model is not changed — additional fields are passed as extra context dict keys beyond what `ReportData.model_dump()` produces.

### Cross-Cutting Concerns

1. **Graceful degradation** — If any new context field is missing or None, the template must render without error (Jinja2 default filters handle this).
2. **No new Python dependencies** — All changes use the stdlib, existing Jinja2, and existing model classes.
3. **Collapse thresholds as constants** — `INPUT_COLLAPSE_THRESHOLD = 200` and `RESPONSE_TRUNCATE_THRESHOLD = 500` must be module-level constants in `oneshot_reporter.py`, injected into context so the template can use them.

### Brownfield Notes

- `ReportData` (`src/gavel_ai/models/runtime.py`) has `model_config = ConfigDict(extra="ignore")` — adding new optional fields is safe and backward compatible.
- `OneShotReporter._build_context` returns a plain dict augmented beyond `ReportData.model_dump()` — we can add extra keys without changing `ReportData`.
- `ReportRunnerStep` constructs `RunData.metadata` dict — we add new keys here.
- Existing integration test `test_oneshot_pipeline_e2e.py` asserts on the presence of certain report content — update assertions as needed.

---

## Tech Stack & Dependencies

| Category | Selection | Rationale |
|----------|-----------|-----------|
| **Language/Runtime** | Python 3.13 | Existing |
| **Template Engine** | Jinja2 (via `jinja_reporter.py`) | Existing |
| **JS** | Vanilla JS (inline, no deps) | Static file constraint |
| **Testing** | pytest, `@pytest.mark.unit` / `@pytest.mark.integration` | Existing |

**New dependencies introduced:** None.

**Dependencies explicitly rejected:**
- Bootstrap/Tailwind — static file constraint, no CDN
- Alpine.js / htmx — no external JS allowed in static reports

---

## Project / Module Structure

Only these files change:

```
src/gavel_ai/
├── reporters/
│   ├── oneshot_reporter.py         # [MODIFIED] Add execution time, subject info, thresholds to context
│   └── templates/
│       └── oneshot.html            # [MODIFIED] Header, Eval Summary, Perf Summary, Scenario Detail
├── core/
│   └── steps/
│       └── report_runner.py        # [MODIFIED] Add input_source, scenario_count, subject_names to RunData.metadata
└── models/
    └── runtime.py                  # [MODIFIED — optional] Add total_execution_time_s to ReportData (optional field)
tests/
├── unit/
│   └── test_oneshot_reporter.py    # [MODIFIED] Update / add tests for new context keys
└── integration/
    └── test_oneshot_pipeline_e2e.py # [MODIFIED] Update HTML assertions for new template structure
```

**Key structural decisions:**
- All new reporter logic lives in `oneshot_reporter.py`; `report_runner.py` only needs to pass the extra metadata keys.
- The template does not call Python — all data prep happens in `_build_context`.

---

## Architecture Decisions (ADRs)

### ADR-1: Pass extra context as dict keys, not new ReportData fields

**Decision:** Add `total_execution_time_s`, `subject_names`, `input_source`, and `scenario_count` as extra keys in the context dict returned by `_build_context`, not as new fields on `ReportData`.

**Rationale:** `ReportData` is a Pydantic model shared with the conversational reporter and potentially other reporters. Adding report-specific display fields to it couples the data model to the HTML template. The context dict is already augmented (e.g., `skipped_counts`), so this pattern is established.

**Affects:** `oneshot_reporter.py:_build_context`, `oneshot.html`

---

### ADR-2: Collapse threshold constants in reporter, not template

**Decision:** Define `INPUT_COLLAPSE_THRESHOLD: int = 200` and `RESPONSE_TRUNCATE_THRESHOLD: int = 500` as module-level constants in `oneshot_reporter.py`. Inject them into the context dict so Jinja2 can reference them.

**Rationale:** Template authors should not need to hunt for magic numbers. Keeping constants in Python lets us write unit tests that verify the threshold values without parsing HTML.

**Affects:** `oneshot_reporter.py`, `oneshot.html`

---

### ADR-3: Input source string constructed in reporter

**Decision:** Build the `input_source` display string (e.g., `"file.local (scenarios.json)"`) in `ReportRunnerStep` or `_build_context`, not in the Jinja2 template.

**Rationale:** Template logic for string construction creates hard-to-test branching. The reporter is Python and easily unit-tested.

**Affects:** `report_runner.py`, `oneshot_reporter.py`

---

### ADR-4: Table layout for scenario detail, not CSS grid

**Decision:** Replace `.comparison-grid` with an HTML `<table>` in the scenario detail section.

**Rationale:** The draft target design uses tables. Tables provide predictable column alignment across rows (input row, response row, score row) and have better print behavior. The existing comparison-grid loses alignment between response and score rows when content heights differ.

**Affects:** `oneshot.html`

---

### ADR-5: Summary metric separation via template logic, not model change

**Decision:** The template checks `deterministic_results` (already in context) to decide whether to render the Deterministic Metrics sub-table in Eval Summary. LLM judges use `summary_metrics` (existing). No new aggregation model is needed.

**Rationale:** `summary_metrics` already contains only LLM judge scores (deterministic metrics flow through `deterministic_results`). The split requires only template conditionals, not new Python aggregation.

**Affects:** `oneshot.html`

---

## Data Models

### Modified: RunData.metadata (in report_runner.py)

`RunData` is a dataclass in `report_runner.py`. Its `metadata` dict gains new keys:

```python
metadata={
    "eval_name": ...,            # existing
    "timestamp": ...,            # existing
    "config_hash": ...,          # existing
    "scenario_count": ...,       # existing
    "variant_count": ...,        # existing
    "eval_type": ...,            # existing
    # NEW:
    "input_source": f"{eval_config.scenarios.source} ({eval_config.scenarios.name})",
    "subject_names": [ts.prompt_name for ts in eval_config.test_subjects if ts.prompt_name],
}
```

### Modified: context dict (in oneshot_reporter.py)

`_build_context` returns a dict. New keys added:

```python
ctx["total_execution_time_s"] = (
    run.telemetry.get("total_duration_seconds") if isinstance(run.telemetry, dict) else None
)
ctx["input_source"] = run.metadata.get("input_source", "")
ctx["subject_names"] = run.metadata.get("subject_names", [])
ctx["scenario_count"] = run.metadata.get("scenario_count", 0)
ctx["input_collapse_threshold"] = INPUT_COLLAPSE_THRESHOLD
ctx["response_truncate_threshold"] = RESPONSE_TRUNCATE_THRESHOLD
```

### Optional: ReportData (in models/runtime.py)

No required changes. If desired for type safety, add:

```python
class ReportData(BaseModel):
    ...
    total_execution_time_s: Optional[float] = None  # NEW optional field
```

This is optional — the context dict approach works without it.

---

## API & Interface Design

### Template Context Contract

The Jinja2 template now expects these additional context variables:

| Variable | Type | Source | Fallback |
|----------|------|--------|---------|
| `total_execution_time_s` | `Optional[float]` | `run.telemetry["total_duration_seconds"]` | `None` → field omitted |
| `input_source` | `str` | `run.metadata["input_source"]` | `""` |
| `subject_names` | `List[str]` | `run.metadata["subject_names"]` | `[]` |
| `scenario_count` | `int` | `run.metadata["scenario_count"]` | `0` |
| `input_collapse_threshold` | `int` | `INPUT_COLLAPSE_THRESHOLD` constant | `200` |
| `response_truncate_threshold` | `int` | `RESPONSE_TRUNCATE_THRESHOLD` constant | `500` |

Existing contract is unchanged: `title`, `run_id`, `generated_at`, `summary_metrics`, `performance_metrics`, `scenarios_by_subject`, `deterministic_results`, `skipped_counts`.

### Template Sections: Exact Structure

#### Header (replacing existing `<header>` block)

```html
<header>
  <h1>OneShot Evaluation Report</h1>
  <div class="header-meta">
    <span><strong>Evaluation:</strong> {{ title }}</span>
    <span><strong>Run ID:</strong> {{ run_id }}</span>
    {% if total_execution_time_s is not none %}
    <span><strong>Overall Execution Time:</strong>
      <span class="time-value">{{ "%.2fs"|format(total_execution_time_s) }}</span>
    </span>
    {% endif %}
    <span><strong>Generated:</strong> {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }}</span>
  </div>
</header>
```

#### Eval Summary (replacing existing `<section id="summary">` block)

```html
<section id="summary">
  <h2>Eval Summary</h2>
  {% if summary_metrics or deterministic_results %}
    {# One block per subject — iterate subjects in order #}
    {% for subject in subject_names %}
      <h3>{{ subject }}</h3>
      <div class="xut-subheader">
        <strong>Input Source:</strong> {{ input_source }} |
        <strong>Number of Scenarios:</strong> {{ scenario_count }}
      </div>
      {% if summary_metrics %}
        <h4>LLM Judges</h4>
        {# existing summary_metrics table, column renamed "LLM Avg" #}
      {% endif %}
      {% if deterministic_results %}
        <h4>Deterministic Metrics</h4>
        <table class="summary-table">
          <thead><tr><th>Metric</th><th>Type</th><th>Score</th></tr></thead>
          <tbody>
            {% for result in deterministic_results %}
            <tr>
              <td>{{ result.metric_name }}</td>
              <td>{{ result.judge_type }}</td>
              <td>{% if result.population_score is none %}<em class="na-note">N/A</em>
                  {% else %}{{ "%.4f"|format(result.population_score) }}{% endif %}</td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      {% endif %}
    {% else %}
      {# fallback when subject_names is empty — show flat tables as before #}
      ...
    {% endfor %}
  {% endif %}
</section>
```

#### Performance Summary (minor addition)

Add `<h3>{{ subject }}</h3>` sub-heading above each performance table. Rename column header `Avg Turn Time` → `Avg Response Time`.

#### Scenario Detail — New Table Layout

```html
<div class="input-section">
  <h3>Scenario {{ scenario.scenario_id }}
    <span style="float:right; font-weight:normal; color:#666; font-size:0.85em;">
      {{ scenario.test_subject }}
    </span>
  </h3>

  {# Collapsible input #}
  <div class="system-prompt">
    <strong>Input:</strong>
    {% if scenario.system_input and scenario.system_input|length > input_collapse_threshold %}
      <div id="input-{{ scenario.scenario_id }}" class="input-text-wrapper">
        <span class="input-text-collapsed">{{ scenario.system_input[:input_collapse_threshold] }}...</span>
        <span class="input-text-expanded">{{ scenario.system_input }}</span>
        <button class="expand-btn" onclick="toggleInput('input-{{ scenario.scenario_id }}')">expand</button>
      </div>
    {% else %}
      <span>{{ scenario.system_input or "" }}</span>
    {% endif %}
  </div>

  {# Variants table #}
  <table>
    <thead>
      <tr>
        {% for variant_id in scenario.variants %}
        <th style="width: {{ (100 / scenario.variants|length)|round(1) }}%;">{{ variant_id }}</th>
        {% endfor %}
      </tr>
    </thead>
    <tbody>
      {# Response row #}
      <tr>
        {% for variant_id, variant in scenario.variants.items() %}
        <td>
          {% set resp = variant.output or "" %}
          {% if resp|length > response_truncate_threshold %}
            <div id="response-{{ scenario.scenario_id }}-{{ variant_id }}" class="truncated-content">
              <span class="truncated-preview">{{ resp[:response_truncate_threshold] }}...</span>
              <span class="truncated-full">{{ resp }}</span>
              <button class="expand-btn"
                onclick="toggleTruncated('response-{{ scenario.scenario_id }}-{{ variant_id }}')">expand</button>
            </div>
          {% else %}
            <div class="model-response">{{ resp }}</div>
          {% endif %}
        </td>
        {% endfor %}
      </tr>
      {# Score row #}
      <tr>
        {% for variant_id, variant in scenario.variants.items() %}
        <td>
          {% if variant.judgments %}
            {% for judge in variant.judgments %}
              <div class="judge-badge"
                onclick="toggleReasoning('reason-{{ scenario.scenario_id }}-{{ variant_id }}-{{ loop.index }}')">
                {{ judge.judge_id }}: <span class="score-val">{{ judge.score }}</span>
              </div>
              <div class="judge-reasoning"
                id="reason-{{ scenario.scenario_id }}-{{ variant_id }}-{{ loop.index }}">
                {{ judge.reasoning }}
              </div>
            {% endfor %}
          {% else %}
            <div class="no-data">No scoring data</div>
          {% endif %}
        </td>
        {% endfor %}
      </tr>
    </tbody>
  </table>
</div>
```

### Backward Compatibility

No existing CLI commands or API endpoints change. The report is a generated artifact — consumers (humans, CI scripts) who assert on specific HTML structure will need to update those assertions. Integration tests in `test_oneshot_pipeline_e2e.py` must be reviewed.

---

## Implementation Patterns & Conventions

### Collapse Toggle JS Functions

Three JS functions are needed (all already in the draft `report.html`):

```javascript
function toggleInput(id) {
    const wrapper = document.getElementById(id);
    wrapper.classList.toggle('expanded');
    const btn = wrapper.querySelector('button');
    btn.textContent = wrapper.classList.contains('expanded') ? 'collapse' : 'expand';
}

function toggleTruncated(id) {
    const el = document.getElementById(id);
    el.classList.toggle('expanded');
    document.querySelectorAll(`button[onclick="toggleTruncated('${id}')"]`)
        .forEach(btn => {
            btn.textContent = el.classList.contains('expanded') ? 'collapse' : 'expand';
        });
}

function toggleReasoning(id) {
    const el = document.getElementById(id);
    el.style.display = el.style.display === 'block' ? 'none' : 'block';
}
```

These replace the current `toggleReasoning` (same logic) and add two new functions.

### CSS Classes Required

All from the draft `report.html` — copy into `oneshot.html`:

- `.header-meta` — header metadata row
- `.time-value` — monospace execution time value
- `.xut-subheader` — subject context line
- `.input-text-wrapper` / `.input-text-collapsed` / `.input-text-expanded` — collapsible input
- `.truncated-content` / `.truncated-preview` / `.truncated-full` — truncatable response
- `.model-response` — response cell content
- `.no-data` — empty state (already exists in current template)

The `.input-text-wrapper.expanded` and `.truncated-content.expanded` CSS rules handle the show/hide via class toggle.

### Testing Pattern

```python
# Unit test for new context keys
def test_build_context_includes_execution_time():
    run = RunData(
        metadata={"eval_name": "test", "scenario_count": 3},
        telemetry={"total_duration_seconds": 42.5},
        ...
    )
    reporter = OneShotReporter(config)
    ctx = reporter._build_context(run)
    assert ctx["total_execution_time_s"] == 42.5

def test_build_context_graceful_missing_execution_time():
    run = RunData(metadata={}, telemetry={}, ...)
    ctx = reporter._build_context(run)
    assert ctx["total_execution_time_s"] is None
```

**Coverage expectations:** New context key extraction: 100%. Template rendering: verified via integration test that the key sections appear in generated HTML.

---

## Security & Performance

### Security

| Concern | Mitigation |
|---------|-----------|
| XSS via scenario input content | Jinja2 auto-escapes by default; `{{ }}` renders HTML-safe; no `| safe` filter on user content |
| XSS via judge reasoning | Same — no `| safe` filter |

### Performance

| Concern | Target | Approach |
|---------|--------|---------|
| Report generation time | ≤ +100ms for 100 scenarios | No new Python loops — collapse is CSS+JS, not Python pre-processing |
| Generated HTML size | < 200KB for media-lens eval (was 2.2MB) | Collapse hides content visually; DOM is smaller because `display:none` elements aren't in the initial render |

Note: The DOM still contains the full text of all inputs/responses — it is hidden via CSS, not absent. Browsers parse the full DOM. For very large evals (1000+ scenarios), a Post-MVP improvement could omit content beyond a threshold entirely and fetch on demand. Out of scope for v1.

### Observability

No new logging or metrics. The existing `self.logger.info(f"Report generated: {report_path}")` covers the key event.

---

## Implementation Sequence

1. **`report_runner.py` — add metadata fields** *(no dependencies)*
   - Add `input_source` and `subject_names` to `RunData.metadata` dict in `ReportRunnerStep.execute()`

2. **`oneshot_reporter.py` — add context keys** *(depends on 1)*
   - Add `INPUT_COLLAPSE_THRESHOLD` and `RESPONSE_TRUNCATE_THRESHOLD` constants
   - Extract and pass `total_execution_time_s`, `input_source`, `subject_names`, `scenario_count`, threshold constants in `_build_context`

3. **`oneshot.html` — header section** *(depends on 2)*
   - Update `<header>` block: fixed h1, add Evaluation + Execution Time fields
   - Add `.header-meta` and `.time-value` CSS

4. **`oneshot.html` — Eval Summary section** *(depends on 2)*
   - Add subject sub-heading, xut-subheader context line
   - Add `<h4>LLM Judges</h4>` conditional
   - Rename "Overall Avg" → "LLM Avg"
   - Add `<h4>Deterministic Metrics</h4>` and summary table conditional

5. **`oneshot.html` — Performance Summary section** *(depends on 2)*
   - Add subject sub-heading
   - Rename column "Avg Turn Time" → "Avg Response Time"

6. **`oneshot.html` — Scenario Detail section** *(depends on 2)*
   - Replace comparison-grid with table layout
   - Add collapsible input, truncatable response, score row, "No scoring data" fallback
   - Add all required CSS classes and JS toggle functions

7. **Tests** *(depends on 3–6)*
   - Update unit tests for new context keys
   - Update integration test HTML assertions

**Parallel work opportunities:** Steps 3–6 (template sections) can be implemented in parallel if desired — each section is independent in the template.

**Known implementation risks:**
- Integration test `test_oneshot_pipeline_e2e.py` asserts on specific HTML structure — verify and update during step 7
- `subject_names` extraction: if `eval_config.test_subjects` is empty or subjects lack `prompt_name`, fall back to extracting unique `test_subject` values from the results list
