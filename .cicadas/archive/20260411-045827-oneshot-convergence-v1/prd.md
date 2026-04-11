---
summary: "This initiative addresses critical functional gaps in the OneShot (v1) workflow by implementing missing CLI commands (judge, list, milestone) and resolving high-priority technical debt, including a scenario mutation bug and redundant retry logic. It aims to deliver a stable, feature-complete foundation for v2."
phase: "clarify"
when_to_load:
  - "When defining or reviewing initiative goals, users, scope, success criteria, and risks."
  - "When validating that implementation still aligns with the intended problem and outcomes."
depends_on: []
modules:
  - "gavel_ai.cli.commands.oneshot"
  - "gavel_ai.processors.scenario_processor"
  - "gavel_ai.core.executor"
  - "gavel_ai.judges.rejudge"
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

# PRD: oneshot-convergence-v1

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

The `oneshot-convergence-v1` initiative is a stabilization and completion pass for the Gavel-AI OneShot workflow. Its primary goal is to wire existing backend logic to the CLI and resolve critical technical debt that currently blocks reliable production usage.

### What Makes This Special

- **Completeness** — Closes the loop on the OneShot lifecycle (Creation → Execution → Judging → Reporting).
- **Correctness** — Fixes a significant data mutation bug in the ScenarioProcessor that currently compromises evaluation integrity.
- **Reliability** — Introduces the first set of end-to-end integration tests to the codebase.

## Project Classification

**Technical Type:** Developer Tool / Framework
**Domain:** AI Infrastructure / Evaluation
**Complexity:** Medium — Primarily wiring and refinement of existing patterns.
**Project Context:** Brownfield — Correcting gaps in an existing scaffolded codebase.

---

## Success Criteria

### User Success

A user achieves success when they can:

1. **Re-judge Results** — Apply new judge definitions to existing processor outputs without re-running models.
2. **Manage Run History** — View a list of previous evaluations and mark specific runs as "milestones" via the CLI.
3. **Trust Execution Integrity** — Be certain that scenarios are processed exactly as defined, without unintended side effects.

### Technical Success

The system is successful when:

1. **CLI Full Loop** — All commands in `gavel oneshot --help` are functional.
2. **Immutability** — `ScenarioProcessor` no longer modifies input objects.
3. **E2E Validation** — A full end-to-end execution of a OneShot eval passes in CI without mocks.

### Measurable Outcomes

- **Pass Rate**: 100% pass rate on new integration tests.
- **AC Coverage**: 100% of Epic 4 and Epic 6 acceptance criteria met in functional validation.

---

## User Journeys

### Journey 1: The Iterative Rater — Refining Judges

Alex has run a large evaluation on 100 scenarios. They realize the "similarity" judge was too lenient. Instead of spending $50 and 20 minutes re-running the whole evaluation, Alex creates a new judge definition and uses `gavel oneshot judge` to re-score the existing outputs in 30 seconds.

**Requirements Revealed:** Re-judging CLI integration, result storage merging, result versioning.

---

### Journey 2: The Researcher — Managing History

Taylor runs evaluations throughout the day. They need to find the "best" run from yesterday to share with the team. Taylor uses `gavel oneshot list` to find the run ID and `gavel oneshot milestone` to mark it so it isn't accidentally deleted.

**Requirements Revealed:** Run listing, metadata persistence, milestone management.

---

## Scope

### MVP — Minimum Viable Product (v1 Convergence)

**Core Deliverables:**
- **Functional `oneshot judge`**: Complete wiring of `ReJudge` to the CLI with `--run` parameter.
- **Functional `oneshot list`**: Table-view of evaluation history.
- **Functional `oneshot milestone`**: CLI command to tag runs.
- **ScenarioProcessor Bug Fix**: Resolve mutation side-effects.
- **Retry Logic Alignment**: Migrate `PromptInputProcessor` to the centralized retry utility.
- **ClosedBox Error Handling**: Specific exception catching in `ClosedBoxInputProcessor`.
- **Test Tagging**: Apply `@pytest.mark.unit/integration` to all foundational tests.

**Quality Gates:**
- **End-to-End Integration Test**: One full pipeline test in `tests/integration/`.
- **Ruff/Linter Compliance**: Resolve all complexity and sorting violations in `oneshot.py`.

---

## Functional Requirements

### 1. CLI Integration (OneShot)

**FR-1.1:** `judge` command integration
- Allow users to specify `--run <run-id>` to re-evaluate existing outputs.
- Supports optional `--judges` filter to run only specific judges.

**FR-1.2:** `list` command integration
- Lists all runs for a given evaluation.
- Displays Run ID, Timestamp, and Milestone status.

**FR-1.3:** `milestone` command integration
- Allows marking/unmarking a run as a milestone.
- Persists milestone status in `run_metadata.json`.

---

### 2. Execution Correctness

**FR-2.1:** Immutable Scenario Processing
- Ensure `ScenarioProcessor` operates on a deep copy of the input or returns context without modifying the input object.

**FR-2.2:** Standardized Retry Logic
- Use `gavel_ai.core.retry.retry_with_backoff` in `PromptInputProcessor`.

**FR-2.3:** Enhanced ClosedBox Error Handling
- Refactor `ClosedBoxInputProcessor` to catch specific exceptions (JSONDecodeError, HTTP status errors) instead of a bare `except Exception`.

---

### 3. Test Quality

**FR-3.1:** Comprehensive Test Tagging
- Apply `@pytest.mark.unit` or `@pytest.mark.integration` to all 136+ foundational tests in the `tests/` directory to enable filtered test runs.

---

## Non-Functional Requirements

- **Performance:** Re-judging should be optimized for batch execution where possible.
- **Reliability:** `ResultStorage` must handle corrupted JSONL lines gracefully (continue with warning).
- **Maintainability:** CLI functions in `oneshot.py` must be refactored to reduce cyclomatic complexity (extract helpers).

---

## Open Questions

- **Re-judge Overwrites?** Should the CLI default to appending new judge scores or overwriting existing ones with the same judge ID? (Proposed: Append to history, but the "latest" report shows the most recent score).

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| JSONL Corruption | Medium | High | Implement line-by-line parsing with error recovery in `ResultStorage`. |
| Pydantic-AI Versioning | Low | Medium | Pin dependency in `pyproject.toml` and add E2E integration test. |
