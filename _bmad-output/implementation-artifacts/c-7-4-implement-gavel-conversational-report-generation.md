# Story C-7.4: Implement `gavel conversational report` Report Generation

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user,
I want `gavel conversational report --eval <name> --run <timestamp>` to generate reports,
so that I can view conversation results in human-readable format.

## Acceptance Criteria

1. **Given** completed run exists with results_judged.jsonl
   **When** `gavel conversational report --eval my_conv_eval --run 20260118-100000` executed
   **Then** ReportingStep generates report.html from Jinja2 template

2. **Given** report template specified with `--template custom.html`
   **When** executed
   **Then** custom template used instead of default

3. **Given** report generation completes
   **When** verified
   **Then** report.html in run directory; opens successfully in browser

4. **Given** report markdown variant requested with `--format markdown`
   **When** executed
   **Then** report.md generated instead of (or in addition to) report.html

## Tasks / Subtasks

- [ ] Task 1: Create `conv report` CLI command (AC: 1)
  - [ ] Subtask 1.1: Add `report` subcommand to `conv` command group in Typer
  - [ ] Subtask 1.2: Add `--eval` parameter for evaluation name
  - [ ] Subtask 1.3: Add `--run` parameter for run timestamp
  - [ ] Subtask 1.4: Add optional `--template` parameter for custom template
- [ ] Task 2: Add format support options (AC: 4)
  - [ ] Subtask 2.1: Add `--format` parameter (default: html, options: html, markdown, both)
  - [ ] Subtask 2.2: Support generating both HTML and Markdown if specified
- [ ] Task 3: Implement run directory and artifact loading (AC: 1)
  - [ ] Subtask 3.1: Validate eval and run directory structure
  - [ ] Subtask 3.2: Load results_judged.jsonl from run directory
  - [ ] Subtask 3.3: Load eval_config.json to get report configuration
  - [ ] Subtask 3.4: Load manifest.json for run metadata
- [ ] Task 4: Implement ReportingStep execution (AC: 1)
  - [ ] Subtask 4.1: Instantiate ReportingStep with conversational context
  - [ ] Subtask 4.2: Execute step to generate HTML report from Jinja2 template
  - [ ] Subtask 4.3: Use conversational report template from Epic C-6
- [ ] Task 5: Implement custom template support (AC: 2)
  - [ ] Subtask 5.1: Validate custom template file exists
  - [ ] Subtask 5.2: Load custom template instead of default
  - [ ] Subtask 5.3: Ensure custom template has required variables from context
  - [ ] Subtask 5.4: Provide clear error if template is invalid
- [ ] Task 6: Implement Markdown report generation (AC: 4)
  - [ ] Subtask 6.1: Create Markdown report template for conversational format
  - [ ] Subtask 6.2: Generate report.md with identical structure to HTML
  - [ ] Subtask 6.3: Include code blocks for conversations, judges, scores
- [ ] Task 7: Implement artifact management (AC: 3)
  - [ ] Subtask 7.1: Write report.html to run directory
  - [ ] Subtask 7.2: Write report.md if --format includes markdown
  - [ ] Subtask 7.3: Update manifest.json with report generation metadata
  - [ ] Subtask 7.4: Verify HTML opens successfully in browser
- [ ] Task 8: Implement error handling (AC: 1)
  - [ ] Subtask 8.1: Validate run exists and has results_judged.jsonl
  - [ ] Subtask 8.2: Handle missing or corrupted result artifacts
  - [ ] Subtask 8.3: Handle template rendering errors with clear messages
  - [ ] Subtask 8.4: Provide recovery guidance for common errors

## Dev Notes

- Report generation uses ReportingStep which is workflow-agnostic
- Conversational report template is more complex than OneShot - shows multi-turn dialogue
- See Epic C-6 stories for detailed report structure requirements
- Custom templates should be Jinja2 format with context variables documented
- Markdown format is useful for programmatic processing and version control
- Report generation is independent and can be run multiple times

### Architecture Alignment

- **CLI Integration**: Extend `src/gavel_ai/cli/commands/conv.py` with `report` subcommand
- **Report Generation**: Use `gavel_ai.reporters.reporter.ReportingStep`
- **Template Location**: Default: `templates/reporters/conversational/default.html` and `default.md`
- **Run Loading**: Use `LocalRunContext.load_run()` to access existing run
- **Template Engine**: Use Jinja2 with context variables from results_judged.jsonl

### Project Structure Notes

- CLI code: `src/gavel_ai/cli/commands/conv.py`
- Report templates: `templates/reporters/conversational/default.html`, `default.md`
- Custom templates: `.gavel/evaluations/<name>/prompts/report_*.html` (if user wants custom)
- Artifacts: `.gavel/evaluations/<name>/runs/<timestamp>/report.html`, `report.md`
- Manifest: `.gavel/evaluations/<name>/runs/<timestamp>/manifest.json`

### References

- [Source: epics-conversational-eval.md#Story-C7.4](epics-conversational-eval.md#Story-C7.4)
- [Source: _bmad-output/implementation-artifacts/c-6-1-implement-report-structure-with-eval-and-performance-summary.md](c-6-1-implement-report-structure-with-eval-and-performance-summary.md)
- [Source: _bmad-output/implementation-artifacts/c-6-2-implement-scenario-detail-sections-with-side-by-side-variant-comparison.md](c-6-2-implement-scenario-detail-sections-with-side-by-side-variant-comparison.md)
- [Source: architecture.md#Reporting](../../planning-artifacts/architecture.md#Reporting)
- Related Requirements: FR-C7.4, FR-5.1 (Jinja2 templating), FR-5.3 (conversational report format)

## Dev Agent Record

### Agent Model Used

Claude-4.5-Sonnet-latest

### Debug Log References

### Completion Notes List

### File List
