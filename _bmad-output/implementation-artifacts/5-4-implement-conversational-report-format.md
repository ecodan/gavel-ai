# Story 5.4: Implement Conversational Report Format

Status: backlog

## Story

As a user,
I want conversational evaluations to follow the Unified Reporting Specification,
So that I can see multi-turn conversations and judge evaluations in a crisp, standardized format.

## Acceptance Criteria

- **Given** a completed conversational evaluation
  **When** report is generated
  **Then** it follows the `_bmad-output/planning-artifacts/tech-specs/unified-reporting-spec.md` specification exactly

- **Given** a multi-turn conversation
  **When** rendered in the Conversation View component
  **Then** all turns are displayed with correct roles, timestamps, and durations

- **Given** turn-level judges
  **When** rendered
  **Then** scores and reasoning are displayed per-turn in the expandable judge view

## Tasks / Subtasks

- [ ] Implement `ConversationalReporter` in `src/gavel_ai/reporters/conversational_reporter.py`
  - [ ] Implement adapter from `ConversationalRun` to `ReportData`
  - [ ] Support turn-level and conversation-level judge extraction
- [ ] Ensure `conversational.html` (if separate) or the unified template correctly handles large multi-turn traces
- [ ] Add integration tests for conversational report generation

## Dev Notes

### Architecture Context

This story extends the unified reporting pattern introduced in Story 5.3 to multi-turn conversations.
We use the same `ReportData` models and Jinja2 components.

### Implementation Patterns
- Use the `Turn` list to capture the full dialogue history.
- Map turn-level judge scores to the `judgments` field of each `VariantResult` or per-turn metadata if applicable.

## Dev Agent Record

### Implementation Plan
- Align `ConversationalReporter` with the `Unified Reporting Spec`.
- Reuse `oneshot.html` (renamed to `unified.html` or similar) for consistency.

## File List

- src/gavel_ai/reporters/conversational_reporter.py
- src/gavel_ai/reporters/templates/conversational.html
- tests/unit/reporters/test_conversational_reporter.py

## Change Log

- 2026-01-19: Re-aligned story with Unified Reporting Spec.
