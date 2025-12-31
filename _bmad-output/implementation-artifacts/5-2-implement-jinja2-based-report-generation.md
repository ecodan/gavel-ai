# Story 5.2: Implement Jinja2-Based Report Generation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a developer,
I want report templates to be Jinja2-based,
So that users can customize report format and layout.

## Acceptance Criteria

- **Given** a Jinja2 template exists
  **When** report generation runs
  **Then** the template is rendered with context variables

- **Given** template variables like {{title}}, {{overview}}, {{summary}}, {{results}}, {{telemetry}}
  **When** the template references them
  **Then** they're substituted with actual data

- **Given** a custom template is provided
  **When** report is generated
  **Then** the custom template is used instead of default

**Template Variables Available:**
- title: Evaluation name
- overview: Eval details (local vs in-situ, variants)
- summary: Table of aggregate scores per variant
- results: Detailed results per scenario
- telemetry: Timing, token counts, metrics
- metadata: Run timestamp, config hash, counts

**Related Requirements:** FR-5.1

## Tasks / Subtasks

- [ ] Implement Jinja2Reporter in src/gavel_ai/reporters/jinja_reporter.py (AC: 1, 2, 3)
  - [ ] Inherit from Reporter ABC
  - [ ] Implement async generate(run: Run, template: str) -> str method
  - [ ] Load Jinja2 template from file or string
  - [ ] Render template with context variables
  - [ ] Handle template not found errors with clear messages
  - [ ] Integrate OpenTelemetry spans for template loading and rendering

- [ ] Create default templates in src/gavel_ai/reporters/templates/ (AC: 1, 2)
  - [ ] Create base.html template with common structure
  - [ ] Create base.md template for markdown reports
  - [ ] Include all required template variables (title, overview, summary, results, telemetry, metadata)
  - [ ] Add CSS styling for HTML templates (readable, responsive)

- [ ] Implement context builder in jinja_reporter.py (AC: 2)
  - [ ] Extract title from Run metadata
  - [ ] Build overview from Run config (variants, scenarios count)
  - [ ] Aggregate summary table (scores per variant)
  - [ ] Format results for template consumption
  - [ ] Extract telemetry metrics (timing, tokens, etc.)
  - [ ] Build metadata dict (timestamp, config hash, counts)

- [ ] Add template validation and error handling (AC: 1, 3)
  - [ ] Validate template file exists before loading
  - [ ] Catch Jinja2 template errors and wrap in ReporterError
  - [ ] Provide clear error messages with recovery steps
  - [ ] Handle missing context variables gracefully

- [ ] Write comprehensive tests in tests/unit/reporters/test_jinja_reporter.py (AC: 1, 2, 3)
  - [ ] Test template rendering with all context variables
  - [ ] Test custom template loading and usage
  - [ ] Test default template usage
  - [ ] Test template not found error handling
  - [ ] Test missing context variable handling
  - [ ] Test OpenTelemetry span emission
  - [ ] Mock Run objects with sample data
  - [ ] Achieve 70%+ coverage

- [ ] Update exports in src/gavel_ai/reporters/__init__.py (AC: 1)
  - [ ] Export Jinja2Reporter

## Dev Notes

### Architecture Context

This story implements **Jinja2-based report generation**, which provides the templating engine for all report formats. This enables users to customize reports without modifying code (FR-5.1).

**Key Architectural Principles:**
- Separated presentation tier (FR-6.5)
- Pluggable report formats (HTML, Markdown, custom)
- Clean abstraction via Reporter ABC (FR-6.1)
- OpenTelemetry instrumentation (Decision 9)

### Dependencies on Previous Stories

**CRITICAL: Story 5.1 must be complete before starting this story.**
- Requires Reporter ABC from src/gavel_ai/reporters/base.py
- Requires ReporterConfig from src/gavel_ai/core/models.py
- Requires ReporterError from src/gavel_ai/core/exceptions.py

**From Epic 4, Story 4.6:**
- Results stored in results.jsonl with scenario_id, variant_id, judges array
- Jinja2Reporter will read and format these results for display

**From Epic 6 (future):**
- Run object will be fully implemented in Epic 6
- For now, Jinja2Reporter should accept Run interface (duck typing)
- Tests should mock Run with required attributes

### Implementation Patterns

**From Story 5.1 (Reporter ABC):**
```python
class Jinja2Reporter(Reporter):
    """Jinja2-based report generator."""

    def __init__(self, config: ReporterConfig):
        super().__init__(config)
        self.env = self._setup_jinja_env()

    def _setup_jinja_env(self) -> jinja2.Environment:
        """Setup Jinja2 environment with template loader."""
        loader = jinja2.FileSystemLoader(self.config.template_path)
        return jinja2.Environment(loader=loader)

    async def generate(self, run: Run, template: str) -> str:
        """Generate report from template and run data."""
        with self.tracer.start_as_current_span("reporter.generate") as span:
            span.set_attribute("reporter.type", "jinja2")
            span.set_attribute("run.id", run.run_id)
            span.set_attribute("template.name", template)

            # Build context
            context = self._build_context(run)

            # Render template
            try:
                tmpl = self.env.get_template(template)
                output = tmpl.render(**context)
                return output
            except jinja2.TemplateNotFound as e:
                raise ReporterError(
                    f"Template '{template}' not found in {self.config.template_path} - "
                    f"Check template_path in config or create template file"
                ) from e
```

### Technical Requirements

**New Dependencies:**
- Jinja2 (already in pyproject.toml)

**File Locations:**
```
src/gavel_ai/reporters/
├── __init__.py           # Export Jinja2Reporter
├── base.py               # Reporter ABC (from Story 5.1)
├── jinja_reporter.py     # NEW: Jinja2Reporter implementation
├── templates/            # NEW: Default templates
│   ├── base.html         # NEW: Default HTML template
│   └── base.md           # NEW: Default Markdown template

tests/unit/reporters/
├── test_base.py          # From Story 5.1
├── test_jinja_reporter.py  # NEW: Jinja2Reporter tests
```

### Context Builder Pattern

The context builder extracts data from Run and formats it for template consumption:

```python
def _build_context(self, run: Run) -> Dict[str, Any]:
    """Build context dict for template rendering."""
    return {
        "title": run.metadata.get("eval_name", "Evaluation Report"),
        "overview": self._build_overview(run),
        "summary": self._build_summary_table(run),
        "results": self._build_results_details(run),
        "telemetry": self._extract_telemetry_metrics(run),
        "metadata": {
            "timestamp": run.metadata.get("timestamp"),
            "config_hash": run.metadata.get("config_hash"),
            "scenario_count": run.metadata.get("scenario_count"),
            "variant_count": run.metadata.get("variant_count"),
        },
    }

def _build_summary_table(self, run: Run) -> List[Dict[str, Any]]:
    """Build summary table with scores per variant."""
    # Aggregate scores from results.jsonl
    # Return list of dicts with variant_id, avg_score, etc.
    pass

def _build_results_details(self, run: Run) -> List[Dict[str, Any]]:
    """Build detailed results for each scenario."""
    # Format results from results.jsonl for template
    # Return list of scenario dicts with outputs and scores
    pass
```

### Template Variables Documentation

**All templates must support these variables:**

```jinja2
{# base.html template structure #}
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        /* Responsive, readable CSS */
    </style>
</head>
<body>
    <h1>{{ title }}</h1>

    <section id="overview">
        <h2>Overview</h2>
        <p>{{ overview.description }}</p>
        <ul>
            <li>Variants Tested: {{ overview.variant_count }}</li>
            <li>Scenarios: {{ overview.scenario_count }}</li>
        </ul>
    </section>

    <section id="summary">
        <h2>Summary</h2>
        <table>
            <thead>
                <tr><th>Variant</th><th>Avg Score</th><th>Total</th></tr>
            </thead>
            <tbody>
                {% for variant in summary %}
                <tr>
                    <td>{{ variant.variant_id }}</td>
                    <td>{{ variant.avg_score }}</td>
                    <td>{{ variant.total_score }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </section>

    <section id="results">
        <h2>Detailed Results</h2>
        {% for result in results %}
        <div class="scenario">
            <h3>Scenario {{ result.scenario_id }}</h3>
            <details>
                <summary>Input</summary>
                <pre>{{ result.input }}</pre>
            </details>
            <table>
                {% for output in result.variant_outputs %}
                <tr>
                    <td>{{ output.variant_id }}</td>
                    <td>{{ output.output }}</td>
                    <td>Score: {{ output.score }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endfor %}
    </section>

    <section id="telemetry">
        <h2>Execution Metrics</h2>
        <ul>
            <li>Total Duration: {{ telemetry.total_duration_seconds }}s</li>
            <li>LLM Calls: {{ telemetry.llm_calls.total }}</li>
            <li>Tokens: {{ telemetry.llm_calls.tokens.prompt_total }} prompt, {{ telemetry.llm_calls.tokens.completion_total }} completion</li>
        </ul>
    </section>

    <footer>
        <p>Generated: {{ metadata.timestamp }}</p>
        <p>Config Hash: {{ metadata.config_hash }}</p>
    </footer>
</body>
</html>
```

### Testing Requirements

**Mock Run Object:**
```python
# tests/unit/reporters/test_jinja_reporter.py
@pytest.fixture
def mock_run():
    """Mock Run object with sample data."""
    class MockRun:
        run_id = "run-20251229-120000"
        metadata = {
            "eval_name": "Test Evaluation",
            "timestamp": "2025-12-29T12:00:00Z",
            "config_hash": "abc123",
            "scenario_count": 10,
            "variant_count": 2,
        }
        # Add results, telemetry, etc.
    return MockRun()

def test_jinja2_reporter_renders_html_template(mock_run):
    """Jinja2Reporter renders HTML template with all variables."""
    config = ReporterConfig(
        template_path="src/gavel_ai/reporters/templates",
        output_format="html"
    )
    reporter = Jinja2Reporter(config)

    output = await reporter.generate(mock_run, "base.html")

    assert "<title>Test Evaluation</title>" in output
    assert "Variants Tested: 2" in output
    assert "Scenarios: 10" in output
```

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.2: Implement Jinja2-Based Report Generation]
- [Source: _bmad-output/planning-artifacts/project-context.md#Type Hints & Validation]
- [Source: _bmad-output/planning-artifacts/project-context.md#Error Handling & Exceptions]

## Dev Agent Record

### Agent Model Used

_To be filled by dev agent_

### Debug Log References

_To be filled by dev agent_

### Completion Notes List

_To be filled by dev agent_

### File List

_To be filled by dev agent_

## Change Log

- 2025-12-29: Story created with dependencies on Story 5.1 and comprehensive Jinja2 implementation guidance
